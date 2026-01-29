# npy_editor/views.py
import os
import json
import numpy as np
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required
from .utils import DataProxy

@login_required
def editor_page(request):
    """渲染主页面"""
    return render(request, 'npy_editor/editor.html')

@login_required
def upload_file(request):
    """处理文件上传（主文件或融合文件）"""
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        file_type = request.POST.get('type', 'main') # 'main' or 'fusion'
        
        # 保存到临时目录
        save_path = os.path.join('npy_uploads', request.user.username, file.name)
        # 如果文件存在先删除，防止重名导致路径变动
        if default_storage.exists(save_path):
            default_storage.delete(save_path)
        path = default_storage.save(save_path, file)
        full_path = os.path.join(settings.MEDIA_ROOT, path)
        
        # 初始化 DataProxy 分析结构
        try:
            proxy = DataProxy(full_path)
            
            # 将路径存入 Session
            if file_type == 'main':
                request.session['main_npy_path'] = full_path
                request.session['fusion_files'] = [] # 清空融合列表
            else:
                fusions = request.session.get('fusion_files', [])
                fusions.append({'path': full_path, 'name': file.name})
                request.session['fusion_files'] = fusions
            
            return JsonResponse({
                'status': 'ok', 
                'keys': proxy.available_keys,
                'length': proxy.length,
                'structure': proxy.structure_type
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'msg': str(e)})
            
    return JsonResponse({'status': 'error', 'msg': 'Upload failed'})

@login_required
def get_chart_data(request):
    """获取绘图数据（包含主文件和所有融合文件）"""
    main_path = request.session.get('main_npy_path')
    if not main_path:
        return JsonResponse({'status': 'error', 'msg': 'No main file loaded'})
        
    x_key = request.GET.get('x_key') # 如果是None则使用索引
    y_key = request.GET.get('y_key')
    
    if not y_key:
        return JsonResponse({'status': 'error', 'msg': 'Please select Y axis'})

    try:
        # 1. 读取主文件
        main_proxy = DataProxy(main_path)
        main_y = main_proxy.get_column_data(y_key)
        main_x = main_proxy.get_column_data(x_key) if x_key and x_key != 'Index' else list(range(len(main_y)))
        
        traces = [{
            'x': main_x, 
            'y': main_y, 
            'name': 'Main: ' + os.path.basename(main_path),
            'type': 'scatter',
            'mode': 'lines+markers',
            'id': 'main' # 标识
        }]
        
        # 2. 读取融合文件 (V23逻辑：截断到最小长度)
        min_len = len(main_y)
        fusions = request.session.get('fusion_files', [])
        
        # 先加载所有融合数据
        loaded_fusions = []
        for f in fusions:
            fp = DataProxy(f['path'])
            fy = fp.get_column_data(y_key)
            # FX 如果没有对应列，返回全0
            if len(fy) == 0: fy = [0] * len(main_y) 
            
            fx = fp.get_column_data(x_key) if x_key and x_key != 'Index' else list(range(len(fy)))
            min_len = min(min_len, len(fy))
            loaded_fusions.append({'x': fx, 'y': fy, 'name': f['name']})
            
        # 3. 执行截断 (V23 核心逻辑)
        # 截断主文件
        traces[0]['x'] = traces[0]['x'][:min_len]
        traces[0]['y'] = traces[0]['y'][:min_len]
        
        # 添加并截断融合文件
        for i, lf in enumerate(loaded_fusions):
            traces.append({
                'x': lf['x'][:min_len],
                'y': lf['y'][:min_len],
                'name': f'Fusion {i+1}: {lf["name"]}',
                'type': 'scatter',
                'mode': 'lines+markers',
                'line': {'dash': 'dash'}, # 融合文件默认虚线
                'id': f'fusion_{i}'
            })
            
        return JsonResponse({'status': 'ok', 'traces': traces, 'min_len': min_len})
        
    except Exception as e:
        import traceback
        return JsonResponse({'status': 'error', 'msg': str(e) + traceback.format_exc()})

@login_required
def update_data(request):
    """处理数据修改 (单点拖拽 or 批量区域操作)"""
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            mode = body.get('mode') # 'single' or 'batch'
            
            # V23 逻辑：根据图例名称或者是索引找到对应的文件
            # 为了简单稳健，这里我们依赖前端传回的 trace_index
            # 0 是主文件，1+ 是融合文件
            trace_index = body.get('trace_index', 0)
            
            target_path = ""
            if trace_index == 0:
                target_path = request.session.get('main_npy_path')
            else:
                fusions = request.session.get('fusion_files', [])
                if trace_index - 1 < len(fusions):
                    target_path = fusions[trace_index-1]['path']
            
            if not target_path: 
                return JsonResponse({'status': 'error', 'msg': '找不到目标文件源'})
            
            proxy = DataProxy(target_path)
            y_key = body.get('y_key') # 当前选择的 Y 轴列名
            
            # --- 模式 1: 单点拖拽修改 ---
            if mode == 'single':
                idx = body.get('index')
                val = body.get('value')
                # 写入数据
                proxy.set_value(idx, y_key, val)
                
            # --- 模式 2: 批量区域操作 (复刻 V23 LinearRegion) ---
            elif mode == 'batch':
                min_x = body.get('min_x')
                max_x = body.get('max_x')
                shift = body.get('shift')
                x_key = body.get('x_key')
                
                # 获取数据
                ys = proxy.get_column_data(y_key)
                # 获取 X 轴数据 (如果是 Index 模式，则生成 0..N)
                xs = proxy.get_column_data(x_key) if x_key and x_key != 'Index' else list(range(len(ys)))
                
                count = 0
                # 执行 V23 同款逻辑
                for i, x_val in enumerate(xs):
                    if min_x <= x_val <= max_x:
                        new_val = ys[i] + shift
                        proxy.set_value(i, y_key, new_val)
                        count += 1
                
                # 批量操作必须立即保存，防止丢失
                proxy.save()
                return JsonResponse({'status': 'ok', 'msg': f'已批量修改 {count} 个数据点'})

            # 单点修改也保存 (或者你可以做一个 "Save All" 按钮才保存，这里为了Web体验实时保存)
            proxy.save() 
            return JsonResponse({'status': 'ok', 'msg': 'Saved'})
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({'status': 'error', 'msg': str(e)})
            
    return JsonResponse({'status': 'error'})