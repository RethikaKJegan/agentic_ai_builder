# Join required reviews before exhausted procurement synthesis

The recorded master delegated its two required reviews with continuation state,
then received zero results/two pending tasks/no remaining task slots and tried
to delegate them again. Join the existing explicitly required review set before
the next master turn when the task capacity is exhausted; preserve other
masters' concurrent independent work, task limits and historical failures.
