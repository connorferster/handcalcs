

@dataclass
class Attribute(HandCalcsObj):
    namespace: str
    attr_name: str


@dataclass
class List(HandCalcsObj):
    elems: deque[Any]

@dataclass
class Tuple(HandCalcsObj):
    elems: deque[Any]

@dataclass
class Set(HandCalcsObj):
    elems: deque[Any]

@dataclass
class Dictionary(HandCalcsObj):
    keys: deque[Any]
    values: deque[Any]

@dataclass
class HCNotImplemented(HandCalcsObj):
    node_name: str
