import os

path = 'mypage.css'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the end of .modal-backdrop { ... }
# which is around line 263
idx_backdrop = -1
for i, line in enumerate(lines):
    if line.startswith('.modal-backdrop {'):
        idx_backdrop = i
        break

idx_end_backdrop = -1
for i in range(idx_backdrop, len(lines)):
    if lines[i].startswith('}'):
        idx_end_backdrop = i
        break

# Find .modal-title p {
idx_modal_title_p = -1
for i in range(len(lines)):
    if lines[i].startswith('.modal-title p {'):
        idx_modal_title_p = i
        break

if idx_end_backdrop != -1 and idx_modal_title_p != -1:
    good_start = lines[:idx_end_backdrop + 1]
    good_end = lines[idx_modal_title_p:]

    middle = """
.modal {
  width: min(1040px, 100%);
  max-height: calc(100% - 16px);
  overflow: auto;
  transform: scale(var(--modal-fit-scale, 0.88));
  transform-origin: center;
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(31, 22, 86, 0.75), rgba(18, 16, 55, 0.85));
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  box-shadow: 0 24px 70px rgba(4, 7, 28, 0.54), inset 0 1px 0 rgba(255, 188, 226, 0.2);
  border: 1px solid rgba(255, 127, 152, 0.25);
}

.modal.profile-modal,
.modal.settings-modal { --modal-fit-scale: 0.82; }

.modal.taste-modal { --modal-fit-scale: 0.9; }

.modal.mbti-modal {
  --modal-fit-scale: 0.82;
  width: min(1120px, 100%);
}

.modal-header {
  position: sticky;
  top: 0;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  min-height: 56px;
  padding: 10px 16px;
  border-bottom: 1px solid rgba(255, 188, 226, 0.15);
  background: linear-gradient(180deg, rgba(28, 22, 78, 0.7), rgba(21, 17, 66, 0.7));
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.modal-title h2 {
  margin: 0;
  font-size: 18px;
  letter-spacing: 0;
  color: var(--primary);
}
"""
    new_content = "".join(good_start) + "\n" + middle.strip() + "\n\n" + "".join(good_end)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Repaired!")
else:
    print("Could not find the indices")
