import datetime
import requests
from zoneinfo import ZoneInfo
from abc import ABC, abstractmethod
import json

class Tool(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def use(self, *args, **kwargs):
        pass

class TimeTool(Tool):
    def name(self):
        return "Time Tool"

    def description(self):
        return "Provide the current time of a given city. If no timezone is provided, it returns the local time."

    def use(self, city):
        try:
            format = "%Y-%m-%d %H:%M:%S %Z%z"
            current_time = datetime.datetime.now()
            timezone_str = self.get_timezone(city)
            if timezone_str:
                current_time = current_time.astimezone(ZoneInfo(timezone_str))
                return f"The current time in {city} is {current_time.strftime(format)}."
            else:
                return f"Could not determine the timezone for {city}."
        except Exception as e:
            return f"Error getting time for {city}: {e}"

    def get_timezone(self, city):
        city_timezones = {
            "kolkata": "Asia/Kolkata",
            "london": "Europe/London",
            "new york": "America/New_York",
            "tokyo": "Asia/Tokyo",
            "paris": "Europe/Paris",
            "sydney": "Australia/Sydney",
            "los angeles": "America/Los_Angeles",
            "chicago": "America/Chicago",
            "dubai": "Asia/Dubai",
            "beijing": "Asia/Shanghai"
        }
        return city_timezones.get(city.lower())

class Agent:
    def __init__(self):
        self.tools = []
        self.memory = []
        self.max_memory = 10

    def add_tool(self, tool: Tool):
        self.tools.append(tool)

    def json_parser(self, input_string):
        try:
            return json.loads(input_string)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            print("Received string:", input_string)
            return {"action": "respond_to_user", "args": {"response": "I couldn't understand the response from the LLM. It's not in the correct format."}}

    def process_input(self, user_input):
        self.memory.append(f"User: {user_input}")
        self.memory = self.memory[-self.max_memory:]

        tool_descriptions = "\n".join([f"- {tool.name()}: {tool.description()}" for tool in self.tools])

        prompt = f"""User input: {user_input}

Available tools:
{tool_descriptions}

Instructions:
- Based on the user's input, decide if you should use a tool or respond directly.
- If you need to use a tool, respond with the tool name and the arguments for the tool in JSON format.
- If you decide to respond directly to the user, respond with the action "respond_to_user" and the response in JSON format.

**Important**: Only return the JSON response with no additional text.

Examples:

Example 1 (Using a tool):
{{
    "action": "Time Tool",
    "args": {{
        "city": "kolkata"
    }}
}}

Example 2 (Responding directly):
{{
    "action": "respond_to_user",
    "args": {{
        "response": "Your direct response here."
    }}
}}"""

        response = self.query_llm(prompt)
        self.memory.append(f"Agent: {response}")

        try:
            response_dict = self.json_parser(response)
        except Exception as e:
            print(f"Error parsing response: {e}")
            return {"action": "respond_to_user", "args": {"response": "There was an error processing the LLM's response."}}

        for tool in self.tools:
            if tool.name().lower() == response_dict.get("action", "").lower():
                return tool.use(**response_dict.get("args", {}))

        return {"action": "respond_to_user", "args": {"response": response}}

    def query_llm(self, prompt):
        url = "http://localhost:11434/v1/completions"
        headers = {
            "Content-Type": "application/json",
        }
        data = {
            "model": "llama3.2:latest",
            "prompt": prompt,
            "max_tokens": 150,
            "temperature": 0.2
        }

        print("Request Data:", json.dumps(data, indent=2))
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response.raise_for_status()
            json_response = response.json()
            print("Response Data:", json.dumps(json_response, indent=2))
            choices = json_response.get('choices', [])
            if not choices or not choices[0].get('text'):
                return '{"action": "respond_to_user", "args": {"response": "The LLM did not return any content."}}'
            final_response = choices[0]['text'].strip()
            print("LLM Response:", final_response)
            return final_response
        except requests.exceptions.RequestException as e:
            print(f"Error making request: {e}")
            return '{"action": "respond_to_user", "args": {"response": "There was an error getting a response from the LLM."}}'
        except (KeyError, IndexError) as e:
            print(f"Error extracting LLM response: {e}")
            print("Response JSON structure:", response.json())
            return '{"action": "respond_to_user", "args": {"response": "There was an error getting a response from the LLM."}}'

    def run(self):
        print("LLM Agent: Hello! How can I assist you today?")
        user_input = input("You: ")

        while True:
            if user_input.lower() in ["exit", "bye", "close"]:
                print("See you later!")
                break

            response = self.process_input(user_input)
            if isinstance(response, dict) and response.get("action") == "respond_to_user":
                print("Response from Agent:", response["args"].get("response", response["args"])) # Handle cases where "response" key might be missing
                user_input = input("You: ")
            else:
                print("Response from Agent:", response)
                user_input = input("You: ")

def main():
    agent = Agent()
    agent.add_tool(TimeTool())
    agent.run()

if __name__ == "__main__":
    main()
