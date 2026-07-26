"""Runs the local web app: python3 scripts\\run_web.py"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("optionslab.web:app", host="127.0.0.1", port=8420, reload=False)
