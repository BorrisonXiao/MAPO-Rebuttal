Thank you for the thoughtful review and for recognizing the consistency of MAPO's improvements over GRPO. We appreciate your emphasis on connecting those improvements to the model's use of audio during reasoning.

**1. Evidence for late-stage audio modality collapse and clarity of Figure 2**

> For Section 3.2, it would help to have a less ambiguous example of question asked (i.e., in Figure 2, the question "How to make this song less funny?") or further statistics over multiple tests to further back up the late-stage audio modality collapse.

The qualitative examples and controlled analyses in the appendix may help clarify both the attention pattern and its behavioral implications. Appendix C.4 provides a direct illustration using the question, "Identify the emotion of each speaker." Base Thinking and mask-only MAPO show declining audio attention later in their responses and both incorrectly conclude that both speakers express sadness. Full MAPO retains more audio attention and correctly distinguishes the speakers' emotions. This example makes the task and the differences between the models easier to follow. We will revise Figure 2 with a clearer example and make the full question and model predictions more prominent.

The aggregate analysis in Appendix E.1 further supports the pattern across examples. It covers 200 MMAU prompts and aligns each response at the point where the model moves from describing the audio to reasoning about the question. After accounting for the growing number of text keys, Base Thinking's per-key audio preference still declines by 0.313 across this transition (166 responses), while MAPO's is preserved (+0.033, 157 responses). On the 143 prompts aligned for both models, the paired MAPO-minus-Base contrast is **+0.338**, with a **95% confidence interval of [0.260, 0.420]**, and the max-head reduction supports the same ordering. The audio also remains necessary after this point. In Appendix E.3, on 200 audio-essential MMAR examples, removing the audio after Base Thinking has already generated a quarter, a third, or half of its response lowers accuracy by 17.0, 14.0, and 6.0 points, so the generated text does not replace the source audio. Finally, the paired interventions in Appendix E.2 show that MAPO relies on the audio more than GRPO does: on 200 audio-essential MMAU examples, removing audio reduces MAPO's accuracy from **67% to 12%**, compared with **60% to 20%** for GRPO. We propose bringing these key findings into Section 3.2 and explicitly pointing readers to the detailed appendix analyses. Together, these results show that the decline in audio attention holds across examples, that continued access to the audio matters for the final answer, and that MAPO strengthens both attention to the audio and reliance on it.

**2. MMAR comparison with Audio-DeepThinker**

> What could be the reasons for the MMAR gap in results between MAPO and Audio-Deep Thinker?

Differences in the starting policy and reasoning supervision offer two plausible explanations for the MMAR gap. Audio-DeepThinker starts from Qwen3-Omni-Instruct, while MAPO starts from Qwen3-Omni-Thinking. In their own two-stage ablation, Audio-DeepThinker reaches **74.0%** on MMAR from Instruct and **70.0%** from Thinking, showing that the starting policy substantially affects performance under their recipe. MAPO starts from the Thinking model because it is designed to operate on an existing reasoning trace (Appendix I), and from this starting point it reaches **70.83%**, compared with their 70.0%. **Importantly, Audio-DeepThinker also rewards similarity to reference CoTs, providing guidance on the reasoning path and key steps.** This additional supervision may benefit MMAR's challenging audio reasoning tasks. MAPO uses correctness, format, and reasoning-consistency rewards without reference-CoT supervision. These differences are documented in Audio-DeepThinker, Table 4 and Section 3.3.

Within our setup, MAPO improves MMAR accuracy from **66.90%** for the base Thinking model and **68.43%** for GRPO to **70.83%**, supporting the benefit of modality-aware optimization for an existing reasoning policy. MAPO also achieves **79.35%** on MMSU compared with **77.26%** for Audio-DeepThinker, indicating complementary strengths across tasks. Together, these results support MAPO's contribution to improving audio reasoning through sustained use of acoustic evidence. In fact, as discussed in Section 2, MAPO "remains fully compatible with these sequence-level reward strategies." Audio-DeepThinker's reference-based rewards can guide the reasoning content alongside MAPO's token-level reweighting and attention objective.

**3. Evaluation protocol and uncertainty in Figures 4 and 5**

> For Figures 4 and 5, many reported methods seem to have close accuracy scores (76-78), resulting in difficulty assessing a true rank without variance information. Were the base model results re-evaluated under the same MAPO protocol?

The Qwen3-Omni baselines were re-evaluated locally using the same benchmark splits, output normalization, and scoring pipeline as MAPO. Results for external systems, including Audio-DeepThinker and Step-Audio-R1, are taken from their published reports.

For MAPO and GRPO, we report the mean and sample standard deviation across three seeds (17, 42, and 1234). On MMAU, MAPO improves accuracy from **75.53 ± 0.55%** for GRPO to **77.83 ± 0.25%**, with an improvement in each seed. This consistency extends to all four benchmarks. We will make MAPO's uncertainty more visible in Figures 4 and 5 and clearly identify published point estimates in the captions.

**4. Mask-only ablation under full fine-tuning**

> In Table 1, it would be interesting to see the MAPO mask-only ablation results for full fine-tuning as well, is it possible?

The LoRA ablation in Table 1 gives the held-out effect of each branch. The modality relevance mask alone raises the four-benchmark average from **69.48%** for GRPO to **70.46%**, and adding the attention loss raises it further to **71.39%**. The training trajectories in Appendices C.2–C.3 provide further evidence for the different roles of the two branches. Setting the attention-loss weight to $\eta=0$ gives mask-only training, which reaches a training accuracy of **0.790**, compared with **0.757** for GRPO, but produces shorter responses. At $\eta=0.05$, adding the attention loss brings response length back near the GRPO level and increases mean audio attention from approximately **0.025 to 0.132**. These settings show how the attention branch changes the balance between task-reward optimization and attention to the source audio.

Under full fine-tuning, MAPO improves the average from **70.95%** for GRPO to **73.25%**, showing that the complete method's benefit persists when all parameters are updated. We are unable to add a full fine-tuning mask-only run within the available rebuttal time and compute budget. The appendix trajectories nevertheless offer a useful view of the components' behavior: the mask improves task-reward optimization, while the attention branch counteracts the tendency toward shorter responses and encourages sustained audio attention.

**5. Choice of reward weights**

> Are the default weights of the reward formulation ablated/explained? Defending or citing the choice of default values λ_acc=2, λ_format=1, and λ_cons=1 would strengthen the method design choices.

We selected the 2:1:1 weights through preliminary hyperparameter tuning rather than a full ablation, guided by the goal of prioritizing answer correctness while retaining incentives for structured and consistent reasoning. A well-formatted response or an internally consistent explanation can still give an incorrect answer, so these auxiliary criteria receive lower weights than accuracy, and the consistency term follows Audio-Thinker. Their role is to encourage the expected response structure and discourage contradictions or prematurely truncated reasoning. GRPO and MAPO are trained with the same reward and the same weights, so the comparison between the two methods is made under an identical reward. We will add this rationale to the experimental setup.

**6. Presentation: figure clarity, paper organization, and visibility of supporting evidence**

> Further results or development moved to the main paper would help a clear assessment of the strength of the method (e.g., showing method robustness to language-prior hallucinations; to support the third contribution statement. Reducing the space allocated to Figures 4 and 5, or placing Algorithm 1 in the appendix, would help gain space).
>
> Mentioning in the main paper the computational overhead that MAPO adds to GRPO would be interesting.
>
> The text in Figure 2 should be the same size as the main text for readability.
>
> Figure 2 would gain from some clarifications or a clearer visual distinction between mean and max. The pink entropy is not labelled: does it denote negative values? The "reasoning end" in purple in the labelled box is not shown in the graph. The (a) and (b) notation should be added within the title of each subgraph.
>
> Figure 3 is neither mentioned nor explained in the text.
>
> Optional: An appendix summary would help to map ablated results.
>
> Optional: the ablation results may come after the main results or, as they directly support the method design choices, the section could be renamed.

Thank you for the detailed feedback on presentation and organization. We will do our best to incorporate these suggestions in the revision, including improving figure readability and annotations, explaining Figure 3 in the text, and making the grounding evidence more prominent in the main paper. We will revisit the space allocated to Figures 4 and 5 and Algorithm 1, and improve appendix navigation and the organization of the ablation results.
