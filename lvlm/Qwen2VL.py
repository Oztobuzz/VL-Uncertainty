import os 
import torch
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
import warnings
warnings.filterwarnings("ignore")

class Qwen2VL:

    def __init__(self, version):
        self.version = version
        self.build_model()

    def build_model(self):
        model_name = f"Qwen/{self.version}"
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                        model_name,
                        torch_dtype=torch.bfloat16,
                        attn_implementation="flash_attention_2",
                        device_map="auto",
                    )
        min_pixels = 128 * 28 * 28
        max_pixels = 640 * 28 * 28
        self.processor = AutoProcessor.from_pretrained(model_name, min_pixels=min_pixels, max_pixels=max_pixels)

    def generate(self, image, question, temp):
        messages = [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "image": image
                                },
                                {
                                    "type": "text",
                                    "text": question
                                }
                            ]
                        }
                    ]
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        if(image is not None):
            image_inputs, video_inputs = process_vision_info(messages)
        else: 
            image_inputs, video_inputs = None, None
        inputs = self.processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        ).to(0)
        generated_ids = self.model.generate(
            **inputs,
            max_new_tokens=32,
            do_sample=True,
            temperature=temp,
            repetition_penalty=1.05,
            top_k=50,
            top_p=0.95,
        )
        generated_ids_trimmed = [out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
        answer = self.processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        return answer[0]