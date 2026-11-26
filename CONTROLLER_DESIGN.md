# PhonePad controller UX plan

## Goal
Make every control reachable without a fingertip balancing on the phone edge, while keeping the familiar visual language of a real gamepad. The phone is held in landscape with two hands; the thumbs operate the face controls and sticks, and the index fingers operate the shoulders.

## Ergonomic decisions

- **Bring shoulders inboard.** Put the bumper hit areas about 15–18% of the screen width in from each edge instead of pinning them to the corners. Keep triggers immediately below them, not above the glass edge. Their centers should sit over the natural index-finger landing area when the phone is held by its grips.
- **Make shoulder targets forgiving.** Use at least a 64 × 56 CSS-pixel touch target (larger on high-density phones), with a visible pressed state. Keep a small visual button inside a larger invisible hit region; don't require precise taps on a thin edge.
- **Separate shoulder controls.** Give bumper and trigger targets clear gaps, distinct labels, and independent pressed states. Provide a small amount of spacing from the screen bezel and reserve a safe-area inset on notched devices.
- **Keep thumb zones natural.** Left stick and D-pad belong to the left thumb; right stick and face buttons belong to the right. Avoid placing secondary actions in the center where both thumbs cross.
- **Support real play gestures.** Pointer capture and multi-touch should allow a stick to stay engaged while another finger presses a button. D-pad and face buttons should support press, drag-between-controls, and release without getting stuck.
- **Show what the gamepad is doing.** A recognizable controller silhouette, physical-looking controls, clear Xbox/PlayStation legends, and immediate pressed/analog feedback reduce the abstraction of a screen full of floating circles.
- **Respect orientation and accessibility.** Prefer landscape; maintain readable labels, high contrast, keyboard-operable buttons, and `aria-pressed` state. Never rely on color alone to show a press.

## Implementation in this branch
`frontend/index.html` is the phone controller, served by the FastAPI app at `/phone`. Touch and keyboard controls produce compact binary packets over a WebSocket; `backend/main.py` applies them to Windows keyboard/mouse input and exposes live state to the desktop dashboard. Bumpers are inset from the glass edge, buttons have generous hit regions, and multi-touch can combine sticks and buttons. `frontend/host.html` displays a QR code, connection/input status, live controls, and the default keyboard mapping.

The Windows app uses the built-in `SendInput` API: no virtual gamepad driver is needed. Games receive keyboard and mouse events, not a gamepad device, so controller-only games and strict anti-cheat titles may not work. Actual comfort still needs device testing; the validation checklist below is a release gate, not a claim that every hand/device combination has already been measured.

## Validation before shipping

1. Test on small and large phones in landscape, both with and without notches, while holding the device in a normal grip.
2. Ask players with different hand sizes to use LB/RB and LT/RT repeatedly without looking; track misses, hand shifts, and accidental neighboring presses.
3. Target fewer than 1 accidental shoulder miss per 100 presses, with no need to change grip. Increase hit-area spacing or move targets farther inboard if the test fails.
4. Test simultaneous shoulder + stick + face-button input on touch devices, including pointer cancellation, screen rotation, and interrupted browser tabs.
5. Confirm the visual pressed state remains legible in daylight and in a dim room, and that all controls remain operable by keyboard and assistive technology.
