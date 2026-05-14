"""Engine that computes the effective valency of a morpheme sequence.

A sequence is a list of ``Entry`` instances in surface order. One entry must
carry a ``base_frame`` and acts as the *head* of the unit (typically the verb
root). Every entry — including the head — may also carry ``rules`` which are
applied left-to-right after the head's base frame has been set, regardless of
whether the rule-bearing entry sits before or after the head in surface order.

This implementation deliberately separates two concerns the paper calls out
(see ``report/sections/compute.typ``): we keep the rich slot representation
for *what each argument is* and *how it is realised*, and we encode the
"中川-style" arity deltas as ``add_slot`` / ``remove_slot`` / ``internalize``
operations on that representation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from morpheme_db.schema import Entry, Rule, Slot, SlotRealization, ValencyFrame


@dataclass(slots=True)
class ComputationStep:
    """One rule application during a computation."""

    entry_id: str
    lemma: str
    rule: Rule | None
    note: str = ""
    frame_after: ValencyFrame = field(default_factory=ValencyFrame)


@dataclass(slots=True)
class ComputationResult:
    final_frame: ValencyFrame
    head_id: str
    steps: list[ComputationStep]
    warnings: list[str] = field(default_factory=list)

    @property
    def arity(self) -> int:
        return self.final_frame.arity

    def describe(self) -> str:
        lines = [f"head: {self.head_id} (arity={self.final_frame.arity})"]
        for slot in self.final_frame.slots:
            lines.append(f"  - {slot.role} [{slot.realization.value}] {slot.label_jp}")
        for step in self.steps:
            op = step.rule.operation if step.rule else "init"
            lines.append(f"step {step.entry_id} ({op}): arity={step.frame_after.arity}")
        for warning in self.warnings:
            lines.append(f"warn: {warning}")
        return "\n".join(lines)


def _find_slot_index(frame: ValencyFrame, role: str) -> int | None:
    for i, slot in enumerate(frame.slots):
        if slot.role == role:
            return i
    return None


def _apply_rule(frame: ValencyFrame, rule: Rule, warnings: list[str], context: str) -> ValencyFrame:
    """Apply a single local rule to a frame, returning a new frame."""
    new_frame = frame.copy()

    if rule.operation == "noop":
        return new_frame

    if rule.operation == "add_slot":
        slot = Slot(
            role=rule.role or "arg",
            realization=rule.realization or SlotRealization.EXTERNAL,
            label_jp=rule.label_jp,
        )
        if rule.position == "back":
            new_frame.slots.append(slot)
        else:
            new_frame.slots.insert(0, slot)
        return new_frame

    if rule.operation == "remove_slot":
        index = rule.target_index
        if index is None and rule.role:
            index = _find_slot_index(new_frame, rule.role)
        if index is None or index >= len(new_frame.slots):
            warnings.append(
                f"{context}: remove_slot could not locate target "
                f"(role={rule.role!r}, target_index={rule.target_index})"
            )
            return new_frame
        new_frame.slots.pop(index)
        return new_frame

    if rule.operation == "internalize":
        index = rule.target_index
        if index is None and rule.role:
            index = _find_slot_index(new_frame, rule.role)
        if index is None:
            # Default: internalise the first external slot.
            for i, slot in enumerate(new_frame.slots):
                if slot.realization == SlotRealization.EXTERNAL:
                    index = i
                    break
        if index is None or index >= len(new_frame.slots):
            warnings.append(
                f"{context}: internalize could not locate target "
                f"(role={rule.role!r}, target_index={rule.target_index})"
            )
            return new_frame
        target = new_frame.slots[index]
        target.realization = rule.realization or SlotRealization.INTERNAL_REFL
        if rule.label_jp:
            target.label_jp = rule.label_jp
        return new_frame

    warnings.append(f"{context}: unknown rule operation {rule.operation!r}")
    return new_frame


def compute_valency(entries: list[Entry]) -> ComputationResult:
    """Compute the effective valency of a morpheme sequence.

    Strategy (mirrors *affix-combination order* in the paper rather than naive
    surface order):

    1. Pick the first entry with a ``base_frame`` as the head. If none has
       one, start from an empty frame and emit a warning.
    2. Apply rules outward from the head: suffixes (head, then entries to the
       right of the head) in left-to-right order, followed by prefixes
       (entries to the left of the head) in right-to-left order — i.e. the
       prefix nearest the root applies first.

    This order is what makes ``si-nukar-e`` correct: the causative ``-e`` has
    to create the causer slot before ``si-`` can internalise it.

    The returned :class:`ComputationResult` carries the final frame and a
    per-step trace, which is useful for both debugging and for the paper's
    "rule-application列" view of computation.
    """
    if not entries:
        return ComputationResult(final_frame=ValencyFrame(), head_id="", steps=[])

    head_index: int | None = None
    for i, entry in enumerate(entries):
        if entry.base_frame is not None:
            head_index = i
            break

    warnings: list[str] = []
    if head_index is None:
        frame = ValencyFrame()
        head_id = ""
        warnings.append("no entry in the sequence provides a base_frame; starting from empty frame")
        order = list(range(len(entries)))
    else:
        frame = entries[head_index].base_frame.copy()
        head_id = entries[head_index].id
        suffix_indices = list(range(head_index, len(entries)))
        prefix_indices = list(range(head_index - 1, -1, -1))
        order = suffix_indices + prefix_indices

    steps: list[ComputationStep] = []
    if head_index is not None:
        steps.append(
            ComputationStep(
                entry_id=entries[head_index].id,
                lemma=entries[head_index].lemma,
                rule=None,
                note="base_frame",
                frame_after=frame.copy(),
            )
        )

    for i in order:
        entry = entries[i]
        for rule in entry.rules:
            context = f"{entry.id}#{i}"
            frame = _apply_rule(frame, rule, warnings, context)
            steps.append(
                ComputationStep(
                    entry_id=entry.id,
                    lemma=entry.lemma,
                    rule=rule,
                    note=rule.description,
                    frame_after=frame.copy(),
                )
            )

    return ComputationResult(
        final_frame=frame,
        head_id=head_id,
        steps=steps,
        warnings=warnings,
    )


__all__ = ["ComputationResult", "ComputationStep", "compute_valency"]
