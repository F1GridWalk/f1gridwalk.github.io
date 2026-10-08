# Fonts for the share images (news/<id>/og.png)

Japanese subsets (JIS X 0208 + kana + Latin + the characters used in headlines so far) of
Noto Serif CJK JP Black and Noto Sans CJK JP Bold (SIL Open Font License 1.1).
build.py uses the system Noto CJK fonts when present; otherwise the update routine copies these
into .ogfonts/ (see ROUTINE.md 7b). Rendering is identical to the system fonts.
