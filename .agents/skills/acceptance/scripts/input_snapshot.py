"""Track every pathlib input to a read-only projection; verify exact bytes before reuse.

Used only by the single-threaded acceptance CLI. No verdict survives this process.
"""
import io
from pathlib import Path


class InputSnapshot:
    def __init__(self):
        self.original = {name:getattr(Path,name) for name in ('read_bytes','read_text','exists','is_file','is_dir','resolve')}
        self.reads, self.conditions, self.resolutions = {}, {}, {}
        self.texts = {}

    @staticmethod
    def active():
        return getattr(Path.read_bytes,'_acceptance_snapshot',None)

    def __enter__(self):
        if self.active() is not None:
            raise ValueError('Use the existing outer read snapshot')

        def read_bytes(path):
            key = path.absolute()
            if key not in self.reads:
                self.reads[key] = self.original['read_bytes'](path)
            return self.reads[key]

        read_bytes._acceptance_snapshot = self

        def read_text(path,encoding=None,errors=None,newline=None):
            key = (path.absolute(),encoding,errors,newline)
            if key not in self.texts:
                with io.TextIOWrapper(io.BytesIO(read_bytes(path)),encoding=encoding,errors=errors,newline=newline) as stream:
                    self.texts[key] = stream.read()
            return self.texts[key]

        def condition(name):
            def tracked(path):
                value = self.original[name](path)
                key = (name,path.absolute())
                if key in self.conditions and self.conditions[key] != value:
                    raise ValueError('Input metadata changed during plan projection: '+str(path))
                self.conditions[key] = value
                return value
            return tracked

        def resolve(path,strict=False):
            key = (path.absolute(),strict)
            # Like file bytes, reuse one coherent value within this inspection.
            # current() resolves every distinct path again before any verdict returns.
            if key not in self.resolutions:
                self.resolutions[key] = self.original['resolve'](path,strict=strict)
            return self.resolutions[key]

        Path.read_bytes, Path.read_text, Path.resolve = read_bytes, read_text, resolve
        for name in ('exists','is_file','is_dir'):
            setattr(Path,name,condition(name))
        return self

    def __exit__(self,*args):
        for name,original in self.original.items():
            setattr(Path,name,original)

    def current(self):
        try:
            # Exact content is checked even if size and modification time were preserved.
            if any(self.original['read_bytes'](path) != data for path,data in self.reads.items()):
                return False
            if any(self.original[name](path) != value for (name,path),value in self.conditions.items()):
                return False
            return all(self.original['resolve'](path,strict=strict) == value
                       for (path,strict),value in self.resolutions.items())
        except (OSError,ValueError,RuntimeError):
            return False
