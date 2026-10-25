"""Show downloaded files using the Windows Shell's item-selection API."""
from pathlib import Path


def reveal_file(path: Path) -> None:
    """Select an existing file without spawning Explorer with command arguments."""
    import ctypes

    if not path.is_file():
        raise FileNotFoundError('El archivo ya no existe.')

    shell = ctypes.WinDLL('shell32')
    ole = ctypes.WinDLL('ole32')
    hresult = ctypes.c_int32
    pointer = ctypes.c_void_p
    ole.CoInitializeEx.argtypes = [pointer, ctypes.c_uint32]
    ole.CoInitializeEx.restype = hresult
    ole.CoUninitialize.argtypes = []
    ole.CoUninitialize.restype = None
    ole.CoTaskMemFree.argtypes = [pointer]
    ole.CoTaskMemFree.restype = None
    shell.SHParseDisplayName.argtypes = [ctypes.c_wchar_p, pointer,
                                        ctypes.POINTER(pointer), ctypes.c_uint32, pointer]
    shell.SHParseDisplayName.restype = hresult
    shell.SHOpenFolderAndSelectItems.argtypes = [pointer, ctypes.c_uint32,
                                                ctypes.POINTER(pointer), ctypes.c_uint32]
    shell.SHOpenFolderAndSelectItems.restype = hresult

    def check(result, message):
        if result < 0:
            raise OSError(f'{message} (0x{result & 0xffffffff:08X}).')

    initialized = ole.CoInitializeEx(None, 2)  # COM apartment for this request thread.
    # An existing COM apartment is also usable; only successful initialization
    # calls belong to us and must be balanced by CoUninitialize.
    if initialized != ctypes.c_int32(0x80010106).value:  # RPC_E_CHANGED_MODE
        check(initialized, 'Windows no pudo preparar el Explorador')
    item = pointer()
    try:
        check(shell.SHParseDisplayName(str(path), None, ctypes.byref(item), 0, None),
              'Windows no pudo localizar el archivo')
        if not item.value:
            raise OSError('Windows no pudo localizar el archivo.')
        # With no child array, the absolute item identifies the file to select
        # inside its parent folder, including paths with spaces or Unicode.
        check(shell.SHOpenFolderAndSelectItems(item, 0, None, 0),
              'Windows no pudo mostrar la ubicación del archivo')
    finally:
        if item.value:
            ole.CoTaskMemFree(item)
        if initialized >= 0:
            ole.CoUninitialize()
