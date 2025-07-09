import datetime
import asyncio
import json
import requests
import subprocess
import os
from dotenv import load_dotenv
from agents import run_agents

load_dotenv()

API_URL = "http://localhost:8081/task/index/"
LOG_FILE = "results.log"
APP_NAME = "SWE-Bench-MAS-LangGraph"

LITELLM_BASE_URL = os.getenv("LITELLM_BASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

async def handle_task(index):
    api_url = f"{API_URL}{index}"
    print(f"Fetching test case {index} from {api_url}...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repos_base_dir = os.path.abspath(os.path.join(script_dir, '..', 'repos'))
    repo_dir = os.path.join(repos_base_dir, f"repo_{index}")
    start_dir = os.getcwd()

    try:
        response = requests.get(api_url)
        if response.status_code != 200:
            raise Exception(f"Invalid response: {response.status_code}")

        testcase = response.json()
        prompt = testcase["Problem_statement"]
        git_clone = testcase["git_clone"]
        fail_tests = json.loads(testcase.get("FAIL_TO_PASS", "[]"))
        pass_tests = json.loads(testcase.get("PASS_TO_PASS", "[]"))
        instance_id = testcase["instance_id"]

        parts = git_clone.split("&&")
        clone_part = parts[0].strip()
        checkout_part = parts[-1].strip() if len(parts) > 1 else None
        repo_name = parts[1].split()[1]

        repo_url = clone_part.split()[2]

        print(f"Cloning repository {repo_url} into {repo_dir}...")
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        if os.path.exists(os.path.join(start_dir, repo_dir)):
            print(os.path.exists(os.path.join(start_dir, repo_dir)))
            print("Repository was already cloned!")
        else:
            subprocess.run(["git", "clone", repo_url, repo_dir], check=True, env=env)

        if checkout_part:
            commit_hash = checkout_part.split()[-1]
            print(f"Checking out commit: {commit_hash}")
            repo_dir_with_name = os.path.join(repo_dir, repo_name)
            subprocess.run(["git", "checkout", commit_hash], cwd=repo_dir_with_name, check=True, env=env)
            # Reset the working directory completely
            subprocess.run(["git", "reset", "--hard"], cwd=repo_dir_with_name, check=True, env=env)
            # subprocess.run(["git", "clean", "-fd"], cwd=repo_dir_with_name, check=True, env=env)

        print(f"Launching Agent-System (LangGraph)...")

        run_agents(index, prompt, repo_name, LITELLM_BASE_URL, OPENAI_API_KEY)

        print(f"Calling SWE-Bench REST service with repo: repo_{index}/{repo_name}")
        test_payload = {
            "instance_id": instance_id,
            "repoDir": f"/repos/repo_{index}/{repo_name}",
            "FAIL_TO_PASS": fail_tests,
            "PASS_TO_PASS": pass_tests
        }
        res = requests.post("http://localhost:8082/test", json=test_payload)
        res.raise_for_status()
        result_raw = res.json().get("harnessOutput", "{}")
        result_json = json.loads(result_raw)
        if not result_json:
            raise ValueError("No data in harnessOutput – possible evaluation error or empty result")
        instance_id = next(iter(result_json))
        tests_status = result_json[instance_id]["tests_status"]
        fail_pass_results = tests_status["FAIL_TO_PASS"]
        fail_pass_total = len(fail_pass_results["success"]) + len(fail_pass_results["failure"])
        fail_pass_passed = len(fail_pass_results["success"])
        pass_pass_results = tests_status["PASS_TO_PASS"]
        pass_pass_total = len(pass_pass_results["success"]) + len(pass_pass_results["failure"])
        pass_pass_passed = len(pass_pass_results["success"])

        os.chdir(start_dir)
        all_tests_passed = fail_pass_passed == fail_pass_total and pass_pass_passed == pass_pass_total
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"

        with open(LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"\n--- TESTCASE {index} ---\n")
            log.write(f"Instance ID: {instance_id}\n")
            log.write(f"FAIL_TO_PASS passed: {fail_pass_passed}/{fail_pass_total}\n")
            log.write(f"PASS_TO_PASS passed: {pass_pass_passed}/{pass_pass_total}\n")
            log.write(f"All tests passed: {str(all_tests_passed).lower()}\n")
            log.write(f"Time: {timestamp}\n")
        print(f"Test case {index} completed and logged.")

    except Exception as e:
        os.chdir(start_dir)
        with open(LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"\n--- TESTCASE {index} ---\n")
            log.write(f"Error: {e}\n")
        print(f"Error in test case {index}: {e}")

async def main():
    # issue_nr = 1
    # await handle_task(issue_nr)

    for issue_nr in [7]:
        print(f"Handling task {issue_nr}...")
        await handle_task(issue_nr)


if __name__ == "__main__":
    asyncio.run(main())
