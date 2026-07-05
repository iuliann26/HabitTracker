from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

#fisier local SQLite pentru stocarea datelor
SQLALCHEMY_DATABASE_URL = "sqlite:///./personal_os.db"

# engine este cel care comunică cu baza de date, iar SessionLocal este o sesiune care va fi folosită pentru a interacționa cu baza de date.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# functia get_db este un generator care creează o sesiune de bază de date și o yield-ează pentru a fi utilizată în alte părți ale aplicației. După ce sesiunea este utilizată, aceasta este închisă pentru a elibera resursele.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()