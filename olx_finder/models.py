from dataclasses import dataclass, field


class OfferFinderError(Exception):
    pass


@dataclass
class Offer:
    title: str
    price: str
    url: str
    description: str = ""
    spec: dict = field(default_factory=dict)


@dataclass
class AnalysisPlan:
    attributes: list[str] = field(default_factory=list)
    guidance: str = ""
