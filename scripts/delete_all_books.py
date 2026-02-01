#!/usr/bin/env python3
"""
One-off script: delete all books from the database and remove their upload files.
Run from project root: python scripts/delete_all_books.py
"""
import os
import sys

# Allow importing app when run from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.base import SessionLocal
from app.models.book import Book


def main():
    db = SessionLocal()
    try:
        books = db.query(Book).all()
        count = len(books)
        if count == 0:
            print("No books in database.")
            return
        for book in books:
            if book.file_path and os.path.exists(book.file_path):
                try:
                    os.remove(book.file_path)
                    print(f"Removed file: {book.file_path}")
                except OSError as e:
                    print(f"Could not remove {book.file_path}: {e}")
            img_dir = os.path.join("uploads", "book_images", book.book_id)
            if os.path.isdir(img_dir):
                try:
                    for f in os.listdir(img_dir):
                        os.remove(os.path.join(img_dir, f))
                    os.rmdir(img_dir)
                    print(f"Removed images dir: {img_dir}")
                except OSError as e:
                    print(f"Could not remove {img_dir}: {e}")
        db.query(Book).delete()
        db.commit()
        print(f"Deleted {count} book(s) from database.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
