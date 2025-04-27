import torch
import transformers
import shlex
import re

class PentestAgent():
    def __init__(
            self,
            llm_model_id,
            llm_model_local,
            temperature,
            top_p,
            container,
            planner_system_prompt,
            planner_user_prompt,
            summarizer_user_prompt,
            summarizer_system_prompt,
            timeout_duration=10,
            do_sample=False,
            max_new_tokens=1024,
            new_observation_length_limit=2000,
            print_end_sep="\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
    ):
        self.container = container
        self.timeout_duration = timeout_duration
        self.max_new_tokens = max_new_tokens
        self.llm_model_id = llm_model_id
        self.temperature = temperature
        self.top_p = top_p
        self.llm_model_local = llm_model_local
        self.llm_pipeline = self.create_llm_pipeline()
        
        self.summarized_history = ""
        self.new_observation = ""
        self.new_observation_length_limit = new_observation_length_limit
        self.print_end_sep = print_end_sep

        # User and system prompts for planner and summarizer
        self.planner_system_prompt = planner_system_prompt
        self.planner_user_prompt = planner_user_prompt
        self.summarizer_system_prompt = summarizer_system_prompt
        self.summarizer_user_prompt = summarizer_user_prompt

    def create_llm_pipeline(self):
        # Create LLM pipeline using the local model
        tokenizer = transformers.AutoTokenizer.from_pretrained(self.llm_model_id)
        model = transformers.AutoModelForCausalLM.from_pretrained(self.llm_model_id, device_map="auto", torch_dtype=torch.bfloat16)
        return transformers.pipeline("text-generation", model=model, tokenizer=tokenizer)

    def generate_text(self, messages):
        # Generate text using local LLM model
        prompt = self.llm_pipeline.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        input_tokens = self.llm_pipeline.tokenizer(prompt, return_tensors='pt')
        input_token_count = len(input_tokens['input_ids'][0])

        outputs = self.llm_pipeline(prompt, max_new_tokens=self.max_new_tokens, do_sample=self.do_sample, temperature=self.temperature, top_p=self.top_p)
        generated_text = outputs[0]["generated_text"][len(prompt):]

        output_tokens = self.llm_pipeline.tokenizer(generated_text, return_tensors='pt')
        output_token_count = len(output_tokens['input_ids'][0])
        
        return generated_text, input_token_count, output_token_count

    def plan_and_run_cmd(self, verbose=True):
        # Plan a command and execute it within the container
        planner_output, _, _ = self.planner()
        match = re.search(r'<CMD>(.*?)</CMD>', planner_output)
        
        if match:
            cmd_to_run = match.group(1)
            safe_cmd = shlex.quote(cmd_to_run)

            if self.container.status != 'running':
                self.container.start()

            command_output = self.container.exec_run(f"timeout {self.timeout_duration}s /bin/bash -c {safe_cmd}").output.decode('utf-8').strip()
        else:
            cmd_to_run = "*No command*"
            command_output = "*No output.*"

        if verbose:
            print(f"Planner output: {planner_output}")
            print(command_output, end=self.print_end_sep)

        self.new_observation = f"{cmd_to_run}:\n{command_output}"

        if len(self.new_observation) > self.new_observation_length_limit:
            self.new_observation = self.new_observation[:self.new_observation_length_limit] + " *Output truncated*"
            print("New observation truncated")

        return planner_output, cmd_to_run, command_output

    def planner(self):
        # Generate plan based on system prompt and user prompts
        user_prompt = self.planner_user_prompt.format(summarized_history=self.summarized_history)
        user_prompt += self.target_text

        messages = [
            {"role": "system", "content": self.planner_system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        output, input_token_count, output_token_count = self.generate_text(messages)
        return output, input_token_count, output_token_count

    def summarizer(self, verbose=True):
        # Summarize the observations and refine strategy
        user_prompt = self.summarizer_user_prompt.format(summarized_history=self.summarized_history, new_observation=self.new_observation)
        messages = [
            {"role": "system", "content": self.summarizer_system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        output, input_token_count, output_token_count = self.generate_text(messages)
        self.summarized_history = output

        if verbose:
            print(f"Current summary:\n{self.summarized_history}", end=self.print_end_sep)

        return output, input_token_count, output_token_count

    def download_files(self, urls):
        # Download files within the container using wget
        for url in urls:
            self.container.exec_run(f"wget {url} -O {url.split('/')[-1]}").output.decode('utf-8').strip()
