import sqlite3

DB_PATH = 'proctoring.db'

def assign_exam_id_to_orphan_questions(exam_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Find questions with NULL or 0 exam_id
    c.execute("SELECT id FROM questions WHERE exam_id IS NULL OR exam_id = 0")
    orphan_ids = [row[0] for row in c.fetchall()]
    if not orphan_ids:
        print("No orphan questions found.")
        conn.close()
        return
    print(f"Assigning exam_id={exam_id} to {len(orphan_ids)} orphan questions...")
    c.execute("UPDATE questions SET exam_id = ? WHERE exam_id IS NULL OR exam_id = 0", (exam_id,))
    conn.commit()
    conn.close()
    print("Done.")

if __name__ == '__main__':
    exam_id = int(input("Enter the exam_id to assign orphan questions to: "))
    assign_exam_id_to_orphan_questions(exam_id)
