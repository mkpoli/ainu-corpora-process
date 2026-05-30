<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		children,
		height = '60vh',
		minScale = 0.3,
		maxScale = 3
	}: {
		children: Snippet;
		height?: string;
		minScale?: number;
		maxScale?: number;
	} = $props();

	let container: HTMLDivElement | null = $state(null);
	let content: HTMLDivElement | null = $state(null);
	let scale = $state(1);
	let tx = $state(0);
	let ty = $state(0);
	let panning = $state(false);
	let panMoved = $state(false);
	let hasFit = false;
	let lastX = 0;
	let lastY = 0;

	const PAN_THRESHOLD = 4; // px before we treat pointerdrag as a real pan
	const FIT_PAD = 24; // breathing room around the tree when fitting

	function clampScale(s: number): number {
		return Math.min(maxScale, Math.max(minScale, s));
	}

	/**
	 * Scale + position the content so the whole tree fits the viewport: wide
	 * polysynthetic trees zoom out instead of overflowing off-canvas. We never
	 * zoom *in* past 100% (a small tree stays crisp, just centred). The tree is
	 * top-aligned (it reads top-down) and horizontally centred. `scrollWidth`/
	 * `scrollHeight` give the natural layout size, unaffected by the transform.
	 */
	function fitToView() {
		if (!container || !content) return;
		const cw = container.clientWidth;
		const ch = container.clientHeight;
		const ww = content.scrollWidth;
		const wh = content.scrollHeight;
		if (!ww || !wh) return;
		scale = clampScale(Math.min(1, (cw - FIT_PAD * 2) / ww, (ch - FIT_PAD * 2) / wh));
		tx = Math.max(FIT_PAD, (cw - ww * scale) / 2);
		ty = FIT_PAD;
	}

	// Fit once on mount (each new query re-keys this component, so a fresh
	// instance re-fits). rAF lets layout settle before we measure.
	$effect(() => {
		if (hasFit || !container || !content) return;
		hasFit = true;
		requestAnimationFrame(fitToView);
	});

	function onWheel(e: WheelEvent) {
		// ctrl/cmd + wheel → zoom toward cursor (standard convention).
		// shift + wheel → horizontal scroll (treats the vertical wheel
		//   delta as horizontal pan; matches the OS convention for
		//   scrolling the secondary axis with a one-axis mouse wheel).
		// Plain wheel / trackpad scroll → pan in both axes (matches how
		//   graph editors like Figma / Lucidchart behave).
		if (!container) return;
		e.preventDefault();
		const rect = container.getBoundingClientRect();
		const cx = e.clientX - rect.left;
		const cy = e.clientY - rect.top;
		if (e.ctrlKey || e.metaKey) {
			const next = clampScale(scale * Math.exp(-e.deltaY * 0.0015));
			const k = next / scale;
			tx = cx - (cx - tx) * k;
			ty = cy - (cy - ty) * k;
			scale = next;
		} else if (e.shiftKey) {
			// Pure horizontal pan; use whichever delta the device provided.
			tx -= e.deltaY || e.deltaX;
		} else {
			tx -= e.deltaX;
			ty -= e.deltaY;
		}
	}

	function isInteractive(target: EventTarget | null): boolean {
		if (!(target instanceof HTMLElement)) return false;
		return Boolean(target.closest('button, a, [role="button"]'));
	}

	function onPointerDown(e: PointerEvent) {
		// Left button only; ignore middle / right.
		if (e.button !== 0) return;
		// If the press lands on a real interactive control, let it handle the
		// click. We only start panning when the user grabs the background.
		// Holding shift forces a pan even over chips, in case the user wants
		// to drag the whole canvas.
		if (!e.shiftKey && isInteractive(e.target)) return;
		if (!container) return;
		panning = true;
		panMoved = false;
		lastX = e.clientX;
		lastY = e.clientY;
		container.setPointerCapture(e.pointerId);
	}

	function onPointerMove(e: PointerEvent) {
		if (!panning) return;
		const dx = e.clientX - lastX;
		const dy = e.clientY - lastY;
		if (!panMoved && Math.hypot(dx, dy) < PAN_THRESHOLD) return;
		panMoved = true;
		tx += dx;
		ty += dy;
		lastX = e.clientX;
		lastY = e.clientY;
	}

	function onPointerUp(e: PointerEvent) {
		if (!panning) return;
		panning = false;
		if (container?.hasPointerCapture(e.pointerId)) {
			container.releasePointerCapture(e.pointerId);
		}
	}

	function onClickCapture(e: MouseEvent) {
		// If the previous pointer interaction moved past the pan threshold,
		// swallow the synthetic click so chips don't activate at the end of
		// a drag.
		if (panMoved) {
			e.preventDefault();
			e.stopPropagation();
			panMoved = false;
		}
	}

	function reset() {
		// "Reset" = fit the tree back into view (more useful than 100% for the
		// wide trees this canvas exists for).
		fitToView();
	}

	function zoomBy(factor: number) {
		if (!container) return;
		const rect = container.getBoundingClientRect();
		const cx = rect.width / 2;
		const cy = rect.height / 2;
		const next = clampScale(scale * factor);
		const k = next / scale;
		tx = cx - (cx - tx) * k;
		ty = cy - (cy - ty) * k;
		scale = next;
	}
</script>

<div
	role="application"
	aria-label="Composition tree canvas — drag to pan, scroll or ⌘-wheel to zoom"
	bind:this={container}
	onwheel={onWheel}
	onpointerdown={onPointerDown}
	onpointermove={onPointerMove}
	onpointerup={onPointerUp}
	onpointercancel={onPointerUp}
	onclickcapture={onClickCapture}
	class="relative overflow-hidden rounded-2xl bg-paper/30 ring-1 ring-rule select-none"
	style:height
	style:touch-action="none"
	style:cursor={panning ? 'grabbing' : 'grab'}
>
	<div
		bind:this={content}
		class="origin-top-left"
		style:transform="translate({tx}px, {ty}px) scale({scale})"
		style:will-change="transform"
	>
		{@render children()}
	</div>

	<!-- Toolbar: reset + zoom controls, parked top-right so it doesn't
	     collide with the tree which usually starts top-centre. -->
	<div
		class="absolute top-3 right-3 flex items-center gap-1 rounded-xl bg-paper/95 p-1 text-[11px] shadow ring-1 ring-rule backdrop-blur"
	>
		<button
			type="button"
			onclick={() => zoomBy(1 / 1.2)}
			class="rounded px-2 py-1 font-mono text-ink/70 hover:bg-accent-soft hover:text-accent"
			title="Zoom out"
			aria-label="Zoom out"
		>
			−
		</button>
		<span class="min-w-[3em] text-center font-mono text-[10px] text-ink/60">
			{Math.round(scale * 100)}%
		</span>
		<button
			type="button"
			onclick={() => zoomBy(1.2)}
			class="rounded px-2 py-1 font-mono text-ink/70 hover:bg-accent-soft hover:text-accent"
			title="Zoom in"
			aria-label="Zoom in"
		>
			+
		</button>
		<button
			type="button"
			onclick={reset}
			class="rounded px-2 py-1 font-mono text-ink/70 hover:bg-accent-soft hover:text-accent"
			title="Reset view"
		>
			reset
		</button>
	</div>

	<!-- Tiny hint at the bottom-left so first-time users know the area is
	     interactive. -->
	<p class="pointer-events-none absolute bottom-2 left-3 text-[10px] italic text-ink/45">
		drag to pan · scroll to move · shift-scroll = horizontal · ⌘-scroll to zoom
	</p>
</div>
