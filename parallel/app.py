from flask import Flask, render_template, request, Response
import ollama
import subprocess
import concurrent.futures
from functools import partial

app = Flask(__name__)

def query_llama(prompt):
    try:
        response = ollama.chat(model="llama3.1", messages=[{
            "role": "user", 
            "content": prompt
        }])
        return response.get('text', 'Error: Unable to get response.')
    except Exception as e:
        return f"Error connecting to LLM: {str(e)}"

def execute_code(code):
    try:
        # Create a string buffer to capture print outputs
        from io import StringIO
        import sys
        old_stdout = sys.stdout
        redirected_output = sys.stdout = StringIO()

        # Execute the code
        exec_locals = {}
        exec(code, {}, exec_locals)
        
        # Get printed output
        sys.stdout = old_stdout
        output = redirected_output.getvalue()
        
        # Combine printed output with any returned values
        if output:
            return output
        return str(exec_locals)
    except Exception as e:
        return f"Error: {str(e)}"

def get_code_summary(code):
    prompt = f"Provide a concise summary of the following code:\n{code}"
    return query_llama(prompt)

def get_code_suggestions(code):
    prompt = f"Provide suggestions for improving or optimizing the following code:\n{code}"
    return query_llama(prompt)

def get_code_time_complexity(code):
    prompt = f"Analyze the time complexity of the following code:\n{code}"
    return query_llama(prompt)

def run_analysis(func, code):
    """Wrapper function to run analysis with code parameter"""
    return func(code)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze_code', methods=['POST'])
def analyze_code():
    code = request.form['code']
    if not code:
        return Response("No code provided.", status=400, mimetype='text/plain')

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        # Create partial functions with the code parameter
        analysis_functions = [
            (execute_code, "execution"),
            (get_code_summary, "summary"),
            (get_code_suggestions, "suggestions"),
            (get_code_time_complexity, "complexity")
        ]
        
        # Submit all tasks to the executor
        future_to_analysis = {
            executor.submit(run_analysis, func, code): name 
            for func, name in analysis_functions
        }

        # Initialize results dictionary
        results = {
            "execution": "Execution failed",
            "summary": "Summary generation failed",
            "suggestions": "Suggestions generation failed",
            "complexity": "Complexity analysis failed"
        }

        for future in concurrent.futures.as_completed(future_to_analysis):
            analysis_name = future_to_analysis[future]
            try:
                results[analysis_name] = future.result()
            except Exception as e:
                results[analysis_name] = f"Error in {analysis_name}: {str(e)}"

    response_html = f"""
    <div class="analysis-results">
        <div class="execution">
            <pre>{results['execution']}</pre>
        </div>
        <div class="summary">
            <pre>{results['summary']}</pre>
        </div>
        <div class="suggestions">
            <pre>{results['suggestions']}</pre>
        </div>
        <div class="complexity">
            <pre>{results['complexity']}</pre>
        </div>
    </div>
    """
    
    return Response(response_html, mimetype='text/html')

if __name__ == '__main__':
    app.run(debug=True)