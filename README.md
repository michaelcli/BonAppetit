# TartanHacks2019
Reducing food waste

## Setup
If you have miniconda3 and it says conda not found
    export PATH="/Users/username/miniconda3/bin:$PATH" 
Create virtual environment (only need to do once)
    conda update conda
    conda create -n venv_name python=3.6 numpy cython pystan
To activate virtual environment (do every time before running)
    source activate venv_name
    pip install fbprophet django pillow 
Run server
    python3 manage.py runserver
### That way, it's in a separate virtual environment
