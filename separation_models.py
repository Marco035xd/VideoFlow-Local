"""Pinned, checksum-verified HT-Demucs ONNX exports from StemSplit."""
MODELS = {
    '4': {
        'repo': 'StemSplitio/htdemucs-onnx',
        'revision': 'd54ed9eb60e258ea82131c6ee14578628816456a',
        'filename': 'htdemucs_fp16weights.onnx',
        'size': 165612636,
        'sha256': 'd05c269d0178d2a72ad484b10b11dd370193fc923201c3b27a99f848745db70a',
        'sources': ['drums', 'bass', 'other', 'vocals'],
    },
    '6': {
        'repo': 'StemSplitio/htdemucs-6s-onnx',
        'revision': '49df9b6989cf2150840ea65b0bef77a2e471b678',
        'filename': 'htdemucs_6s_fp16weights.onnx',
        'size': 136428532,
        'sha256': '7ce55792e2231c93fbf92de95f5fd5b3a5e6c89f7db690dfd693e8f1dce56869',
        'sources': ['drums', 'bass', 'other', 'vocals', 'guitar', 'piano'],
    },
}
STEM_LABELS = {'vocals': 'Voz', 'instrumental': 'Música', 'drums': 'Batería',
               'bass': 'Bajo', 'other': 'Otros', 'guitar': 'Guitarra', 'piano': 'Piano'}


def model_for(mode):
    return MODELS['6' if mode == 'separate_6' else '4']
