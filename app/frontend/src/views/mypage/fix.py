import re

path = 'mypage.css'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# We know the duplication started right after .modal-backdrop { ... }
# Let's find ".modal-backdrop" block.
# Then we will just reconstruct the modal and modal-header from scratch,
# and connect it back to .modal-title h2 {

backdrop_idx = text.find('.modal-backdrop {')
if backdrop_idx == -1:
    print("Cannot find modal-backdrop")

# find the end of modal-backdrop
backdrop_end_idx = text.find('}', backdrop_idx) + 1

# find the start of .modal-title h2
title_idx = text.find('.modal-title h2 {')

if backdrop_end_idx != 0 and title_idx != -1:
    before = text[:backdrop_end_idx]
    after = text[title_idx:]
    
    # Correct intermediate CSS
    mid = """

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

"""
    new_text = before + mid + after
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("Fixed!")
else:
    print("Could not find blocks")
