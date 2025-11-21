
from ask.socratic.question_engine import QuestionEngine


def test_generate_questions():
    engine = QuestionEngine()
    content = "The sky is blue. Water is wet!"
    questions = engine.generate_questions(content)
    # There should be 3 questions per sentence
    assert len(questions) == 6
    assert questions[0] == "Why is 'The sky is blue' important?"
    assert questions[1] == "What are the implications of 'The sky is blue'?"
    assert questions[2] == "How does 'The sky is blue' relate to other ideas?"
    assert questions[3] == "Why is 'Water is wet' important?"
    assert questions[4] == "What are the implications of 'Water is wet'?"
    assert questions[5] == "How does 'Water is wet' relate to other ideas?"
