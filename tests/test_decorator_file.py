from handcalcs.decorator import HandcalcsCallRecorder, handcalc
import pytest

# Define a simple arithmetic function for testing
def simple_func(a: float, b: float) -> float:
    c = a + b
    return c

@pytest.fixture
def recorder():
    return HandcalcsCallRecorder(simple_func)

def test_simple_arithmetic(recorder):
    result = recorder(1, 2)
    assert result[1] == 3
    assert result[0] == '\n\\begin{aligned}\nc &= a + b  = 1 + 2 &= 3  \n\\end{aligned}\n'

def test_call_recording(recorder):
    recorder(1.0, 2.0)
    recorder(3.5, 4.5)
    assert recorder.calls == 2 # There should be two recorded calls.
    assert recorder.history[0]['return'] == 3.0
    assert recorder.history[1]['return'] == 8.0

def test_decorator_with_recording():
    decorated_func = handcalc(record=True)(simple_func)
    result = decorated_func(1.0, 2.0)
    assert result[1] == 3.0
    assert decorated_func.calls == 1
    assert decorated_func.history[0]['return'] == 3.0
    assert decorated_func.history[0]['latex'] == '\n\\begin{aligned}\nc &= a + b  = 1.000 + 2.000 &= 3.000  \n\\end{aligned}\n'

    decorated_func = handcalc(record=False)(simple_func)
    latex, result = decorated_func(1.0, 2.0)
    assert result == 3.0
    assert latex == '\n\\begin{aligned}\nc &= a + b  = 1.000 + 2.000 &= 3.000  \n\\end{aligned}\n'
