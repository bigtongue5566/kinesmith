# 3D、材質、光與鏡頭

Three.js 用於即時 3D、Shader 與互動式預覽；Blender 用於更完整的燈光、材質、Geometry Nodes 與離線電影式畫面。需求先於引擎偏好，不以方塊旋轉代表所有 3D 創作。

Three.js 原生光影骨架，可放在既有 renderer 的初始化流程：

```js
const scene = new THREE.Scene(); scene.background = new THREE.Color('#ebe6db');
const camera = new THREE.PerspectiveCamera(38, width/height, .1, 100);
camera.position.set(4, 3, 6); camera.lookAt(0, 0, 0);
scene.add(new THREE.HemisphereLight(0xdff6ff, 0x35414c, 2));
const key = new THREE.DirectionalLight(0xffe7b9, 4);
key.position.set(3, 5, 4); scene.add(key);
const mesh = new THREE.Mesh(new THREE.TorusKnotGeometry(1, .25, 160, 24),
  new THREE.MeshStandardMaterial({color:0x007f73, roughness:.28, metalness:.35}));
scene.add(mesh);
function renderAt(t) {
  mesh.rotation.set(.2*Math.sin(t), t*.7, .13);
  renderer.render(scene, camera);
}
```

色彩管理與 tone mapping 依當前 Three.js 版本設定並鎖定，不能把螢幕截圖顏色視為所有播放環境的絕對標準。透明材質會有排序問題；複雜透明可改用 Blender 或多 pass。

Shader 變形用 `uniform float time`；CPU 每幀指定 `time=t`，不要在 shader 外累加真實 delta。位置變形也影響法線，MeshStandardMaterial 大幅位移需重算法線或用對應 normal shader，否則照明錯誤。

Blender 可執行 Python 關鍵影格（透過 `blender --background --python scene.py`）：

```python
import bpy, math
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_torus_add(major_radius=1.4, minor_radius=.32)
obj = bpy.context.object
obj.rotation_euler = (math.pi/5, 0, 0); obj.keyframe_insert('rotation_euler', frame=1)
obj.rotation_euler = (math.pi/5, 0, math.pi*2); obj.keyframe_insert('rotation_euler', frame=49)
for fc in obj.animation_data.action.fcurves:
    for key in fc.keyframe_points: key.interpolation='LINEAR'
# 設定 camera、light、材質與輸出後，以 scene.frame_set(frame) 精確求值。
```

Blender 5 的 layered Action API 與舊版 fcurves 不同；先以實際安裝版本確認，來源中的 keyframes 本身仍可直接求值。不需要改 interpolation 時可省略 fcurves 區段，使用預設 easing。不要把此版本差異藏起來。

Geometry Nodes 建議先用官方 node API 或在 .blend 建節點再 Python 修改 exposed input。Scatter/Instance/Realize Instances 分開考慮記憶體；材質、燈光與鏡頭本身仍由 Blender 原生管理，Kinesmith 不封裝成自訂物件模型。Cycles seed、samples、denoise、render device、Blender 版本均記錄；跨裝置 GPU bitwise 相同不能保證。

Blender 4.2 原生 Geometry Nodes 網路範例（對已建立的 mesh object `obj` 呼叫；實際機位／材質由作品設計）：

```python
def add_radial_instances(obj):
    import bpy
    tree = bpy.data.node_groups.new('Kinesmith radial instances', 'GeometryNodeTree')
    tree.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    tree.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    nodes, links = tree.nodes, tree.links
    source = nodes.new('NodeGroupInput'); output = nodes.new('NodeGroupOutput')
    circle = nodes.new('GeometryNodeMeshCircle')
    circle.inputs['Vertices'].default_value = 18
    circle.inputs['Radius'].default_value = 2.4
    instance = nodes.new('GeometryNodeInstanceOnPoints')
    instance.inputs['Scale'].default_value = (.12, .12, .12)
    links.new(circle.outputs['Mesh'], instance.inputs['Points'])
    links.new(source.outputs['Geometry'], instance.inputs['Instance'])
    links.new(instance.outputs['Instances'], output.inputs['Geometry'])
    modifier = obj.modifiers.new('Editable radial layout', 'NODES')
    modifier.node_group = tree
    return circle
```

呼叫後可對 `circle.inputs['Radius'].default_value` 插 keyframe，或讓節點使用 Scene Time。Geometry Nodes 留在 .blend 可直接編輯，不把實例化結果烘焙成不可修訂貼圖。
