from app.db.base import Base
from app.db.session import engine
from app.models.booking import Booking
from app.models.document import Document


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    initialize_database()
    print("Database tables created (or already existed).")