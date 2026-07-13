from dataclasses import dataclass

@dataclass(frozen=True)
class NoValue:
    pass

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return True
        return False
    
    def __neq__(self, other):
        return False


@dataclass
class HcNotImplemented:
    node_name: str