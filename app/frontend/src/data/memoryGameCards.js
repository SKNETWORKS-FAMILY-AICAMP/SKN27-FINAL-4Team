// memoryGameCards.js
// 캐릭터 카드 짝 맞추기(메모리 게임)에 쓰이는 카드 자산 정의.
//
// TODO(자산 연결 필요):
// 아래 24개 카드 앞면(front/) 이미지와 1개 카드 뒷면(back/) 이미지는 아직 저장소에
// 실제 파일이 없다. 담당자가 카드 이미지를 전달하면 다음 경로에 그대로 넣는다.
//   src/assets/games/memory/front/<파일명>.webp  (24개, 캐릭터당 6개)
//   src/assets/games/memory/back/card-back.webp  (1개)
// 파일이 없는 동안에는 이미지 preload가 실패하고, 게임 소개 화면에 "게임 이미지를
// 불러오지 못했어요." 오류 상태로 표시된다(정상 동작). 파일명이 아래와 다르면
// FRONT_FILENAMES / BACK_FILENAME 값만 실제 파일명에 맞게 수정하면 된다.

const front = import.meta.glob("../assets/games/memory/front/*.{webp,png,jpg,jpeg}", {
  eager: true,
  import: "default",
});
const back = import.meta.glob("../assets/games/memory/back/*.{webp,png,jpg,jpeg}", {
  eager: true,
  import: "default",
});

function resolveFrom(map, filename) {
  const entry = Object.entries(map).find(([path]) => path.endsWith(`/${filename}`));
  return entry ? entry[1] : null;
}

// 캐릭터별 6장씩, 총 24장. 실제 파일명이 다르면 이 목록만 바꾸면 된다.
const CHARACTER_ASSETS = [
  {
    character: "PORI",
    label: "포리",
    files: ["pori_01.webp", "pori_02.webp", "pori_03.webp", "pori_04.webp", "pori_05.webp", "pori_06.webp"],
  },
  {
    character: "KKAMI",
    label: "까미",
    files: ["kkami_01.webp", "kkami_02.webp", "kkami_03.webp", "kkami_04.webp", "kkami_05.webp", "kkami_06.webp"],
  },
  {
    character: "TOTO",
    label: "토토",
    files: ["toto_01.webp", "toto_02.webp", "toto_03.webp", "toto_04.webp", "toto_05.webp", "toto_06.webp"],
  },
  {
    character: "YEOUL",
    label: "여울",
    files: ["yeoul_01.webp", "yeoul_02.webp", "yeoul_03.webp", "yeoul_04.webp", "yeoul_05.webp", "yeoul_06.webp"],
  },
];

const BACK_FILENAME = "card-back.webp";

export const memoryGameAssets = CHARACTER_ASSETS.flatMap(({ character, label, files }) =>
  files.map((filename, index) => {
    const id = `${character.toLowerCase()}-${String(index + 1).padStart(2, "0")}`;
    return {
      id,
      character,
      // 스크린리더용 대체 텍스트. 감정/진단 문구는 넣지 않는다.
      alt: `${label} 캐릭터 카드`,
      imageUrl: resolveFrom(front, filename),
      _expectedFilename: filename,
    };
  })
);

export const memoryGameCardBack = {
  imageUrl: resolveFrom(back, BACK_FILENAME),
  alt: "빈틈사이 카드 뒷면",
  _expectedFilename: BACK_FILENAME,
};

// 자산이 아직 준비되지 않은 항목(파일 없음)을 개발 로그로 확인하기 위한 헬퍼.
export function getMissingMemoryGameAssets() {
  const missingFronts = memoryGameAssets.filter((asset) => !asset.imageUrl).map((asset) => asset._expectedFilename);
  const missingBack = memoryGameCardBack.imageUrl ? [] : [memoryGameCardBack._expectedFilename];
  return [...missingFronts, ...missingBack];
}
