"""Contracts for scraped movie data and the PoiskKino API response."""

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, RootModel


class Movie(BaseModel):
    """Normalized movie data shared by scraper and indexer."""

    model_config = ConfigDict(extra="ignore")

    id: int
    title: str = Field(
        default="Без названия",
        validation_alias=AliasChoices("title", "name", "alternativeName"),
    )
    year: int | None = None
    country: str | None = None
    director: str | None = None
    description: str = ""
    actors: list[str] = Field(default_factory=list)
    genres: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("genres", "tags"),
    )
    rating: float | None = None
    poster_url: str | None = None


class MoviesDocument(RootModel[list[Movie]]):
    """JSON document containing normalized movies."""


class PoiskKinoRating(BaseModel):
    """Rating fields returned by PoiskKino."""

    model_config = ConfigDict(extra="ignore")

    kp: float | None = None


class PoiskKinoCountry(BaseModel):
    """Country object returned by PoiskKino."""

    name: str | None = None


class PoiskKinoGenre(BaseModel):
    """Genre object returned by PoiskKino."""

    name: str | None = None


class PoiskKinoPerson(BaseModel):
    """Person object returned by PoiskKino."""

    name: str | None = None
    enName: str | None = None
    profession: str | None = None


class PoiskKinoPoster(BaseModel):
    """Poster object returned by PoiskKino."""

    url: str | None = None
    previewUrl: str | None = None


class PoiskKinoMovie(BaseModel):
    """Movie document returned by PoiskKino."""

    model_config = ConfigDict(extra="ignore")

    id: int
    name: str | None = None
    alternativeName: str | None = None
    year: int | None = None
    countries: list[PoiskKinoCountry] = Field(default_factory=list)
    persons: list[PoiskKinoPerson] = Field(default_factory=list)
    genres: list[PoiskKinoGenre] = Field(default_factory=list)
    rating: PoiskKinoRating = Field(default_factory=PoiskKinoRating)
    description: str | None = None
    shortDescription: str | None = None
    poster: PoiskKinoPoster = Field(default_factory=PoiskKinoPoster)


class PoiskKinoResponse(BaseModel):
    """Paginated PoiskKino API response."""

    docs: list[PoiskKinoMovie] = Field(default_factory=list)
    page: int = 1
    pages: int = 1
