IGNORE_INDEX = -100

def preprocess_chatglm_cp(example, prompter, tokenizer, options):
    model_inputs = {}
    src_tokens = tokenizer.tokenize(example["input"])
    prompt_tokens = tokenizer.tokenize(example["instruction"])

    if len(src_tokens) > options.max_source_length - len(prompt_tokens):
        src_tokens = src_tokens[:options.max_source_length - len(prompt_tokens)]

    tgt_tokens = tokenizer.tokenize(example["output"])
    if len(tgt_tokens) > options.max_target_length:
        tgt_tokens = tgt_tokens[:options.max_target_length]

    tokens = prompt_tokens + src_tokens + ["[gMASK]", "<sop>"] + tgt_tokens + ["<eop>"]
    input_ids = tokenizer.convert_tokens_to_ids(tokens)
    context_length = input_ids.index(tokenizer.bos_token_id)
    mask_position = context_length - 1
    labels = [-100] * context_length + input_ids[mask_position + 1:]

    pad_len = options.max_source_length - len(input_ids)
    input_ids = input_ids + [tokenizer.pad_token_id] * pad_len
    labels = labels + [-100] * pad_len

    model_inputs["input_ids"] = input_ids
    model_inputs["labels"] = labels
    return model_inputs


def preprocess_chatglm(example, prompter, tokenizer, options):
    # v1: build inputs with format `X [gMASK] <sop> Y <eop>` and labels with format `[IGNORE] ... [IGNORE] Y <eop>`
    # v2: build inputs with format `[gMASK] sop X Y </s>` and labels with format `[IGNORE] ... [IGNORE] Y </s>`
    model_inputs = {}
    prompt = prompter.generate_prompt(example["instruction"], example["input"])
    source_ids = tokenizer.encode(text=prompt, add_special_tokens=False)
    target_ids = tokenizer.encode(text=example["output"], add_special_tokens=False)

    if len(source_ids) > options.max_source_length - 2: # gmask and sop tokens
        source_ids = source_ids[:options.max_source_length - 2]
    if len(target_ids) > options.max_target_length - 1: # eos token
        target_ids = target_ids[:options.max_target_length - 1]

    context_length = len(source_ids) + 2 # gmask and sop tokens
    input_ids = tokenizer.build_inputs_with_special_tokens(source_ids, target_ids)
    labels = [IGNORE_INDEX] * context_length + input_ids[context_length:]

    model_inputs["input_ids"] = input_ids
    model_inputs["labels"] = labels
    return model_inputs


def preprocess_chatglm_eval(example, prompter, tokenizer, options):
    # v1: build inputs with format `X [gMASK] <sop>` and labels with format `Y [gMASK] <sop>`
    # v2: build inputs with format `[gMASK] sop X` and labels with format `[gMASK] sop Y`
    model_inputs = {}
    prompt, answer = prompter.generate_prompt(example)
    source_ids = tokenizer.encode(text=prompt, add_special_tokens=False)
    target_ids = tokenizer.encode(text=answer, add_special_tokens=False)

    if len(source_ids) > options.max_source_length - 2: # gmask and sop tokens
        source_ids = source_ids[:options.max_source_length - 2]
    if len(target_ids) > options.max_target_length - 2: # gmask and sop tokens
        target_ids = target_ids[:options.max_target_length - 2]

    input_ids = tokenizer.build_inputs_with_special_tokens(source_ids)
    labels = tokenizer.build_inputs_with_special_tokens(target_ids)

    model_inputs["input_ids"] = input_ids
    model_inputs["labels"] = labels
    return model_inputs


def preprocess_chatglm_pairwise(example, prompter, tokenizer, options):
    # v1: build input pairs with format `X [gMASK] <sop> Y1 <eop>` and `X [gMASK] <sop> Y2 <eop>`
    # v2: build input pairs with format `[gMASK] sop X Y1 </s>` and `[gMASK] sop X Y2 </s>`
    model_inputs = {}
    prompt, answer = prompter.generate_prompt(example)
    source_ids = tokenizer.encode(text=prompt, add_special_tokens=False)
    accept_ids = tokenizer.encode(text=answer[0], add_special_tokens=False)
    reject_ids = tokenizer.encode(text=answer[1], add_special_tokens=False)

    if len(source_ids) > options.max_source_length - 2: # gmask and sop tokens
        source_ids = source_ids[:options.max_source_length - 2]
    if len(accept_ids) > options.max_target_length - 1: # eos token
        accept_ids = accept_ids[:options.max_target_length - 1]
    if len(reject_ids) > options.max_target_length - 1: # eos token
        reject_ids = reject_ids[:options.max_target_length - 1]

    accept_ids = tokenizer.build_inputs_with_special_tokens(source_ids[:], accept_ids) # avoid copying error
    reject_ids = tokenizer.build_inputs_with_special_tokens(source_ids[:], reject_ids)

    model_inputs["input_ids"] = accept_ids
    model_inputs["labels"] = reject_ids
    return model_inputs


def coll_fn_chatglm(stage = "sft"):
    if stage == "sft":
        return preprocess_chatglm    
    elif stage == "rm":
        return preprocess_chatglm_pairwise
    elif stage == "ppo":
        return preprocess_chatglm_eval

