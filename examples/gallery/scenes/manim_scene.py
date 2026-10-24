"""Native Manim geometry; no LaTeX executable or external font download required."""
import json
import math
import os
from pathlib import Path

import numpy as np
from manim import (
    Arc, Circle, Create, Dot, Line, Scene, Text, UpdateFromAlphaFunc,
    VGroup, VMobject, config, linear,
)


class MotionScene(Scene):
    def construct(self):
        ctx = json.loads(Path(os.environ["KINESMITH_CONTEXT"]).read_text(encoding="utf-8"))
        config.background_color = "#101c2e"
        self.camera.background_color = "#101c2e"
        paper, aqua, coral = "#f2e6cf", "#65d4cf", "#ff775a"
        header = Text("05 / GEOMETRY BECOMES A STORY", font="Arial", font_size=14, color=paper)
        header.move_to([-3.1, 3.2, 0])
        footer = Text("MANIM / MATHEMATICAL RHYTHM", font="Arial", font_size=14, color="#8294a9")
        footer.move_to([-3.1, -3.32, 0])
        title = Text("A SIMPLE\nRULE.", font="Arial", font_size=37, color=paper, line_spacing=.7)
        title.move_to([-4.25, .55, 0])
        subtitle = Text("An infinite set of possibilities.", font="Arial", font_size=14, color=aqua)
        subtitle.move_to([-4.1, -.85, 0])
        center = np.array([1.5, .1, 0])
        guides = VGroup(*[Circle(radius=r, color="#34475c", stroke_width=1).move_to(center) for r in (1, 1.7, 2.4)])
        axes = VGroup(Line(center + [-2.8, 0, 0], center + [2.8, 0, 0], color="#34475c", stroke_width=1),
                      Line(center + [0, -2.6, 0], center + [0, 2.6, 0], color="#34475c", stroke_width=1))
        points = [center + [2.5 * math.cos(a) * math.cos(3 * a), 2.5 * math.sin(a) * math.cos(3 * a), 0]
                  for a in np.linspace(0, 2 * math.pi, 500)]
        curve = VMobject(color=aqua, stroke_width=3).set_points_smoothly(points)
        moving = Dot(points[0], radius=.09, color=coral)
        arc = Arc(radius=2.7, start_angle=.2, angle=math.pi * 1.55, color=paper, stroke_width=1).move_to(center)
        self.add(guides, axes, arc, header, footer, title, subtitle, moving)
        self.play(Create(curve), UpdateFromAlphaFunc(moving, lambda mob, alpha: mob.move_to(curve.point_from_proportion(alpha))),
                  run_time=ctx["duration"], rate_func=linear)
