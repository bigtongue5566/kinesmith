// Thin offline host for the pinned OpenUtau core. No composition or synthesis is reimplemented.
using System.Reflection;
using System.Runtime.InteropServices;
using System.Runtime.Loader;
using System.Text;
using System.Text.Json;
using Nito.AsyncEx;
using OpenUtau.Core;
using OpenUtau.Core.Format;
using OpenUtau.Core.Ustx;
using OpenUtau.Core.Util;

record Job(string Project, string Output, string Data, string Singers, string EngineDirectory,
           int TimeoutSeconds = 600, bool InspectOnly = false, int Steps = 20);

class Diagnostics : ICmdSubscriber {
    public readonly List<string> Errors = new();
    public void OnNext(UCommand cmd, bool isUndo) {
        if (cmd is ErrorMessageNotification) {
            Errors.Add(cmd.ToString());
            Console.Error.WriteLine(cmd);
        }
    }
}

class Program {
    static int Main(string[] args) {
        try {
            if (args.Length != 1) throw new ArgumentException("Expected one JSON job file.");
            var job = JsonSerializer.Deserialize<Job>(File.ReadAllText(args[0]),
                new JsonSerializerOptions { PropertyNameCaseInsensitive = true })!;
            // Register before entering a method that refers to upstream types.
            AssemblyLoadContext.Default.Resolving += (_, name) => {
                var path = Path.Combine(job.EngineDirectory, name.Name + ".dll");
                return File.Exists(path) ? AssemblyLoadContext.Default.LoadFromAssemblyPath(path) : null;
            };
            AsyncContext.Run(() => Run(job));
            return 0;
        } catch (Exception e) {
            Console.Error.WriteLine(e);
            return 1;
        }
    }

    static async Task Run(Job job) {
        Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
        var core = typeof(DocManager).Assembly;
        NativeLibrary.SetDllImportResolver(core, (name, _, _) => {
            foreach (var candidate in new[] { name, name + ".dll", "lib" + name + ".so", "lib" + name + ".dylib" }) {
                var path = Path.Combine(job.EngineDirectory, candidate);
                if (File.Exists(path) && NativeLibrary.TryLoad(path, out var handle)) return handle;
            }
            return IntPtr.Zero;
        });
        Directory.CreateDirectory(job.Data);
        // Upstream exposes private setters. Pin its version and redirect all writes away
        // from the user's OpenUtau preferences, singers and global application folders.
        foreach (var (name, value) in new[] { ("DataPath", job.Data), ("CachePath", Path.Combine(job.Data, "Cache")), ("RootPath", job.EngineDirectory) }) {
            typeof(PathManager).GetProperty(name)!.SetValue(PathManager.Inst, value);
        }
        Directory.CreateDirectory(PathManager.Inst.CachePath);
        Preferences.Default.AdditionalSingerPath = job.Singers;
        Preferences.Default.DiffSingerSteps = job.Steps;
        var context = SynchronizationContext.Current!;
        var scheduler = TaskScheduler.FromCurrentSynchronizationContext();
        DocManager.Inst.PostOnUIThread = action => context.Post(_ => action(), null);
        DocManager.Inst.RequestFrame = action => context.Post(_ => action(), null);
        DocManager.Inst.Initialize(Thread.CurrentThread, scheduler);
        OpenUtau.Classic.ToolsManager.Inst.Initialize();
        var diagnostics = new Diagnostics();
        DocManager.Inst.AddSubscriber(diagnostics);
        SingerManager.Inst.Initialize();
        if (job.InspectOnly) {
            Console.WriteLine(JsonSerializer.Serialize(SingerManager.Inst.Singers.Values.Select(s => new { id = s.Id, name = s.Name, type = s.SingerType.ToString(), location = s.Location })));
            return;
        }
        var project = Ustx.Load(job.Project);
        DocManager.Inst.ExecuteCmd(new LoadProjectNotification(project));
        var parts = project.parts.OfType<UVoicePart>().ToArray();
        if (parts.Length == 0) throw new InvalidDataException("Project has no voice parts.");
        if (project.tracks.Any(t => t.Singer == null || !t.Singer.Found)) throw new InvalidDataException("Missing singer.");
        var deadline = DateTime.UtcNow.AddSeconds(job.TimeoutSeconds);
        while (parts.Any(p => !p.PhonemesUpToDate || p.renderPhrases.Count == 0)) {
            if (DateTime.UtcNow > deadline) throw new TimeoutException("Phonemization did not complete.");
            if (diagnostics.Errors.Count > 0) throw new InvalidDataException(string.Join("\n", diagnostics.Errors));
            await Task.Delay(50);
        }
        var invalid = parts.SelectMany(p => p.phonemes).Where(p => p.Error).ToArray();
        if (invalid.Length > 0) throw new InvalidDataException($"Invalid phonemes: {string.Join(", ", invalid.Select(p => p.phoneme + ": " + p.ErrorException))}; verify lyrics/aliases and voicebank.");
        Directory.CreateDirectory(job.Output);
        await PlaybackManager.Inst.RenderToFiles(project, Path.Combine(job.Output, "vocal.wav"))
            .WaitAsync(TimeSpan.FromSeconds(job.TimeoutSeconds));
        await Task.Yield(); // Drain upstream notifications before accepting the export.
        if (diagnostics.Errors.Count > 0) throw new InvalidDataException(string.Join("\n", diagnostics.Errors));
        var inventory = parts.Select(p => new { track = p.trackNo, notes = p.notes.Count,
            phonemes = p.phonemes.Select(ph => new { alias = ph.phoneme, error = ph.Error }), phrases = p.renderPhrases.Count });
        File.WriteAllText(Path.Combine(job.Output, "phonemes.json"), JsonSerializer.Serialize(inventory));
        Console.WriteLine(JsonSerializer.Serialize(new { status = "ok", engine = core.GetName().Version!.ToString(), parts = inventory }));
    }
}

