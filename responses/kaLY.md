Thank you for the careful review and for recognizing the value of the behavioral grounding controls. Several of the questions below call for additional training runs of the 30B model at the scale described in Section 4, which were beyond the compute available to us during the rebuttal period. We therefore address these questions with new analyses of the existing checkpoints, a smaller-scale training study on a second model family, and the same-setting comparisons already in the paper.

**1. Effect of the frozen reference on the entropy signal and token weights**

> How do the masks and held-out results change when both entropy terms are evaluated with the same evolving checkpoint? Can you quantify how much of the fixed-reference signal is associated with policy drift rather than audio conditioning?

To separate the effect of audio from changes introduced by training, we measured next-token predictive entropy in three conditions: trained MAPO with audio, the same checkpoint without acoustic features, and the base model without acoustic features. The question, saved response prefix, and token positions were held fixed. Comparing MAPO with and without audio measures how audio changes the trained model's uncertainty. Comparing the two text-only predictions measures the entropy shift associated with training. An additional experiment gave the following mean absolute entropy differences:

| Comparison | Mean absolute entropy difference |
|---|---:|
| MAPO w/ versus w/o audio | 0.445 nats |
| MAPO w/o audio versus base w/o audio | 0.244 nats |
| MAPO w/ audio versus base w/o audio | 0.622 nats |

The text-only shift is therefore smaller than the within-MAPO audio/text effect, at about **55% of its magnitude**. Because the reference entropy enters training only through the token weights of the two branches, we also examined how reference choice affects the resulting token weights in a separate replay of **100 MMAU questions and 44,269 saved response tokens**, using the released MAPO weighting rule. At the final checkpoint, which is the furthest in training from the frozen reference, frozen-reference and same-checkpoint weights have Spearman rank correlations of **0.860** for the policy branch and **0.866** for the inverse-attention branch. Changing the reference redistributes **2.8%** and **2.5%** of normalized weight mass, respectively. This close agreement at the end of training indicates that the two choices of reference give similar training signals.

We use the frozen reference to reduce GPU memory overhead by reusing the model already maintained for GRPO's KL penalty, avoiding a separate entropy-reference model. A fixed reference also allows the text-only pass to be computed once per rollout batch and reused across the four optimizer updates (Appendix H.2), whereas a reference that follows the policy would need to be recomputed after every update. Given the smaller text-only shift and the strong agreement in normalized token weights, we regard this as a reasonable balance between preserving the weighting signal and limiting memory use and training time in our training setup.

**2. Validating the entropy gap as an audio-dependence signal**

> Predictive entropy alone is too coarse to identify audio-dependent tokens. Because entropy is a single scalar summary, two completely different token distributions can have the exact same entropy value. A large gap in entropy does not necessarily mean a token truly depends on acoustic evidence. The metric works fine as a practical heuristic, but treating it as proof of true modality dependence requires stronger validation, such as a same-checkpoint audio ablation during training or a distribution divergence check.

Our same-checkpoint comparison with exact KL shows that the absolute entropy gap provides a useful signal for prioritizing tokens whose predictions respond to audio. At a fixed checkpoint and with an identical text prefix, a nonzero entropy gap between audio-present and audio-removed predictions necessarily implies different token distributions and therefore positive KL divergence. Audio can make predictions either more concentrated or more uncertain. The absolute entropy gap captures both effects. KL also detects changes that preserve entropy, so their empirical agreement helps establish how well entropy tracks distribution changes during reasoning.

We compared the absolute entropy gap with exact KL(audio-present || audio-removed) using the base Qwen3-Omni-Thinking model on 100 MMAU questions, covering 45,702 token positions. Both conditions used identical saved response prefixes. The agreement holds across sound, music, and speech:

| Question subset | Mean within-response Spearman correlation [95% CI] | Top-20% token overlap |
|---|---:|---:|
| All | **0.865 [0.857, 0.873]** | **63.5%** |
| Sound | 0.841 [0.828, 0.854] | 59.6% |
| Music | 0.854 [0.839, 0.868] | 60.8% |
| Speech | 0.901 [0.888, 0.914] | 70.1% |

Results are averaged over questions, with 95% question-bootstrap confidence intervals. The overall correlation remains **0.846** after removing broad position trends within each response. The **63.5%** top-token overlap is well above the **20.1%** expected under independent selections, showing that the two signals prioritize substantially overlapping tokens. Because MAPO assigns a soft weight to every token rather than selecting a top set, the rank correlation is the statistic most directly related to how the signal is used. The agreement in both token rankings and high-score selections supports the entropy gap as a practical reweighting signal for positions affected by audio. The behavioral controls in Appendix E complement this signal-level validation by examining how changes to the audio affect final answers. We agree with the reviewer that the entropy gap is best described as a practical signal of audio dependence, and we will describe it this way in the revision and include this comparison in the appendix.

**3. Contributions of entropy reweighting and the attention branch**

> What are the results of attention-only training and of a simple uniform/POS-gated attention penalty under the same update budget? Does differential-entropy reweighting still add value under full fine-tuning?

The attention branch was designed on top of the mask-reweighting branch, motivated by our observation that the entropy gap correlates with the trend of audio attention decay during late-stage reasoning (Section 3.3). When the model stops using audio, the gap can become small and leave the mask with little signal, so the attention loss targets substantive tokens with small absolute entropy gaps and places greater weight on later CoT positions. Its intended effect is to restore audio use at these positions and increase their entropy gaps, allowing the mask to give them greater relative weight in subsequent policy updates. Thus, at a conceptual level, attention-only training without the mask is not a configuration the method is designed for, since the policy update would then weight all tokens uniformly and could not give greater weight to the positions where audio use is restored.

Similarly, a uniform attention penalty would spread optimization weight across all response tokens, including function words. The POS-gate ablation in Appendix G tests this directly under full fine-tuning: removing the gate lowers the four-benchmark average from **73.25%** to **72.39%**, with a lower mean on every benchmark. To test the attention-only case empirically, we ran a small-scale experiment on **MOSS-Audio-8B-Thinking**, a smaller audio reasoning model from a different model family, training each variant for **128 steps** with **LoRA rank 16, alpha 32** under the same rollout and update budget. The attention-only variant adds the POS-gated attention penalty from the reviewer's question to GRPO, using uniform token weights in both the policy and attention losses so that entropy-based weighting is removed from both branches. The benchmark accuracies are as follows, with MMSU evaluated on the full **5,000-example set**:

| Benchmark | GRPO | Attention-only | Full MAPO |
|---|---:|---:|---:|
| MMAU | 74.70% | 75.20% | 76.90% |
| MMSU | 73.64% | 73.72% | 74.06% |
| MMAR | 64.00% | 64.20% | 65.40% |
| MMAU-Pro | 56.12% | 56.25% | 57.48% |

Attention-only training reaches a four-benchmark average of **67.34%**, slightly above GRPO at 67.12%, while full MAPO reaches **68.46%** and is above attention-only on all four benchmarks, by 0.34 to 1.70 points.

Together with the LoRA ablation in Table 1, where the modality relevance mask alone raises the four-benchmark average from **69.48%** for GRPO to **70.46%** and the full method reaches **71.39%**, the MOSS study supports the complementary roles of the two components. Entropy-based weighting improves on GRPO without the attention loss, attention regularization alone gives a smaller gain on MOSS, and the combination gives the best four-benchmark average on both model families. Under full fine-tuning, the available comparison is for the complete method, whose advantage over GRPO is maintained when all parameters are updated, with the four-benchmark average improving from **70.95%** to **73.25%** (Table 1).

**4. Training initialization and response length**

> If MAPO and GRPO start the 29k-example stage from the identical AVQA checkpoint and use matched generation budgets, do the gains remain? Please report response lengths alongside evaluation accuracy to clarify the accuracy/computation trade-off.

MAPO's gain over GRPO is already present when the two methods start from the same initialization, as both of our preliminary comparisons do before the 29k-example continuation. Under LoRA, MAPO improves the four-benchmark average from **69.48%** for GRPO to **71.39%** (Table 1), and with full fine-tuning on AVQA it improves the average from **70.94%** to **71.88%** (Appendix C.1), with gains on all four benchmarks in both settings. The 29k-example continuation then examines how further training on a broader audio QA mixture builds on this gain, so we continue each method from its own AVQA-trained checkpoint to keep its optimization method consistent as the training data expands. The two same-initialization comparisons above therefore compare the methods without multi-stage effects.

The generation budgets are also matched, since MAPO and GRPO share the same rollout sampling setup, with **eight completions per prompt**, a **generation batch of 768**, and **four updates per rollout batch**. Both use generous completion-length limits in training, with the reported mean lengths well below those limits, and both are decoded with the same 2,048-token limit at evaluation, so response length is determined by each learned policy.

On response length, the 800-step training comparison in Appendices C.2–C.3 gives a mean completion length of **477.0 tokens** for GRPO, and the MAPO trajectories show the following pattern:

| Attention-loss weight η | Mean completion length (tokens) | Approximate mean audio attention mass |
|---|---:|---:|
| 0, mask-only | 433.7 | 0.025 |
| 0.05 | 472.5 | 0.132 |
| 0.1 | 525.0 | 0.360 |
| 0.5 | 541.7 | 0.329 |

Entropy reweighting alone produces a more compact response policy in this comparison, and a moderate attention weight brings completion length close to GRPO's while substantially increasing audio attention. The design of the attention branch helps explain this pattern. POS gating selects substantive tokens, including nouns, verbs, and modifiers that carry descriptions of sound sources, acoustic attributes, and events. The inverse entropy weights emphasize selected positions with small entropy gaps, while the temporal weight concentrates pressure later in the response. The attention penalty is averaged over POS-selected tokens, so η controls the strength of the source-attention signal at these positions. Our interpretation is that mask-only optimization favors a compact route to the answer, while stronger attention steering encourages continued description and comparison of acoustic evidence later in reasoning. This provides a linguistic account of the observed length changes in terms of the content the policy learns to sustain.

At η = 0.1, the value used in our main experiments, audio attention is highest and completions are about 10% longer than GRPO's (525.0 vs. 477.0 tokens). Because all auxiliary computations are training-only (Appendix H.2), response length is the only source of additional inference cost.

**5. Scope of applicability to models with native reasoning**

> Improvements do not generalize beyond reasoning models. The reported performance gains are limited strictly to the CoT policy. Appendix I shows that applying the method to the Instruct policy actually leads to a slight performance drop on MMAU. While this negative result is useful to see, it contradicts the claim that the framework serves as a general-purpose optimization recipe across different model types, and I would suggest to tone down the claim.

We agree that the scope should be stated more clearly. MAPO is designed to improve audio grounding in models that already support native chain-of-thought reasoning, because its reweighting and attention objectives build on the reasoning trajectories provided by the starting policy, as discussed in the limitations (Appendix J) and shown by the Instruct-model analysis in Appendix I. Our additional experiments on MOSS-Audio-8B-Thinking support this applicability across a second model family with native reasoning, complementing the Qwen3-Omni-Thinking results. In the revision, we will state the native-reasoning assumption alongside the applicability claim in the abstract, and describe the Instruct result in Appendix I as a slight drop.
