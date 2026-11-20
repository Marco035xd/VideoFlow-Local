"""ONNX Runtime providers shared by the UI API and the separation worker."""

PROVIDERS = {
    'cuda': 'CUDAExecutionProvider',
    'directml': 'DmlExecutionProvider',
    'cpu': 'CPUExecutionProvider',
}
DEVICE_NAMES = {'cuda': 'CUDA', 'directml': 'DirectML', 'cpu': 'CPU'}


def available_devices(ort):
    available = ort.get_available_providers()
    return [device for device, provider in PROVIDERS.items() if provider in available]


def open_session(ort, model_path, mode, device, cpu_threads):
    options = ort.SessionOptions()
    options.intra_op_num_threads = cpu_threads
    options.inter_op_num_threads = 1
    if device == 'directml':
        options.enable_mem_pattern = False
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        if mode in {'separate_2', 'separate_4'}:
            # These modes share a graph whose fused DirectML node can exhaust VRAM.
            options.add_session_config_entry('ep.dml.disable_graph_fusion', '1')
    if device == 'cuda' and hasattr(ort, 'preload_dlls'):
        ort.preload_dlls()
    provider = PROVIDERS[device]
    providers = [provider] if device == 'cpu' else [provider, PROVIDERS['cpu']]
    session = ort.InferenceSession(str(model_path), sess_options=options, providers=providers)
    session.disable_fallback()
    if provider not in session.get_providers():
        raise RuntimeError(f'{DEVICE_NAMES[device]} no pudo iniciar.')
    return session
