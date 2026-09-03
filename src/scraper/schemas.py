"""Contracts for scraped movie data and the PoiskKino API response."""

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, RootModel, field_validator


class Movie(BaseModel):
    """Normalized movie data shared by scraper and indexer."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

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

    @field_validator("actors", "genres", mode="before")
    @classmethod
    def _default_lists(cls, value: object) -> object:
        """Convert null list values from legacy JSON to empty lists."""
        return [] if value is None else value


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

    @field_validator("countries", "persons", "genres", mode="before")
    @classmethod
    def _default_nested_lists(cls, value: object) -> object:
        """Convert null nested list values to empty lists."""
        return [] if value is None else value

    @field_validator("rating", "poster", mode="before")
    @classmethod
    def _default_nested_models(cls, value: object) -> object:
        """Convert null nested objects to empty objects."""
        return {} if value is None else value


class PoiskKinoResponse(BaseModel):
    """Paginated PoiskKino API response."""

    docs: list[PoiskKinoMovie] = Field(default_factory=list)
    page: int = 1
    pages: int = 1

    @field_validator("docs", mode="before")
    @classmethod
    def _default_docs(cls, value: object) -> object:
        """Convert a null document list to an empty list."""
        return [] if value is None else value
