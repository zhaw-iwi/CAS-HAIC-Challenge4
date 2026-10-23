"""Compatibility entry point: rebuild only the notebook; preserve source and learner data."""
from build_notebook import write_notebook

if __name__ == '__main__':
    write_notebook()
