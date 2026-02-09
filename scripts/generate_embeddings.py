import asyncio
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Course
from app.embeddings import generate_embedding, get_model

def process_embeddings():
    db: Session = SessionLocal()
    try:
        # Load model first
        get_model()
        
        # specific query for null embeddings
        courses = db.query(Course).filter(Course.embedding.is_(None)).all()
        print(f"Generating embeddings for {len(courses)} courses...")
        
        count = 0
        for course in courses:
            text = f"{course.title}\n{course.description}"
            # Truncate if too long? SentenceTransformer handles it usually (truncation=True default)
            
            embedding = generate_embedding(text)
            course.embedding = embedding
            count += 1
            
            if count % 50 == 0:
                print(f"Processed {count} courses...")
                db.commit()
                
        db.commit()
        print(f"Finished generating embeddings for {count} courses.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    process_embeddings()
