from decimal import Decimal
import pytest
from app import Course,compile_results,create_app,grade_for

@pytest.mark.parametrize('score,grade,point',[(75,'A','4.00'),(70,'AB','3.50'),(65,'B','3.25'),(60,'BC','3.00'),(55,'C','2.75'),(50,'CD','2.50'),(45,'D','2.25'),(40,'E','2.00'),(39,'F','0.00')])
def test_grades(score,grade,point): assert grade_for(Decimal(score))==(grade,Decimal(point))
def test_weighted_cgpa():
    result=compile_results([Course(id=1,semester=1,course_code='A',course_unit=3,score=75),Course(id=2,semester=2,course_code='B',course_unit=2,score=60)])
    assert result['total_units']==5 and result['cgpa']==Decimal('3.6') and result['classification']=='Distinction'
@pytest.fixture
def client(): return create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':'sqlite:///:memory:'}).test_client()
def test_home(client): assert client.get('/').status_code==200 and client.get('/health').json=={'status':'ok'}
def test_submit(client):
    r=client.post('/calculate',data={'student_name':'Test Student','course_code_1[]':'MTH101','course_unit_1[]':'3','score_1[]':'80'},follow_redirects=True)
    assert r.status_code==200 and b'MTH101' in r.data and b'4.00' in r.data
