#!/usr/bin/env bash
# Alibaba cluster-trace-gpu-v2020 수집
#
# 경로 두 가지를 지원한다.
#   1. PRIMARY  : 알리바바 OSS 직접 다운로드 (공식 경로)
#   2. MIRROR   : GitHub 미러 저장소 클론 (30MB 분할 파일)
#
# 왜 두 경로인가:
#   개발 환경에 따라 OSS 도메인이 방화벽/egress 정책에 막히는 경우가 있다.
#   실제로 이 프로젝트의 개발 컨테이너에서 OSS가 차단되어 미러 경로를 추가했다.
#   (docs/failures.md 2026-09-15 참조)
#
# 사용법:
#   bash scripts/fetch_data.sh             # 자동 (OSS 시도 후 실패 시 미러)
#   SOURCE=mirror bash scripts/fetch_data.sh
#   SOURCE=oss    bash scripts/fetch_data.sh
#
# 멱등성: 이미 추출된 CSV가 있으면 건너뛴다.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW_DIR="${RAW_DIR:-$REPO_ROOT/data/raw/alibaba_gpu_2020}"
WORK_DIR="${WORK_DIR:-$REPO_ROOT/data/.download}"
SOURCE="${SOURCE:-auto}"

OSS_BASE="https://aliopentrace.oss-cn-beijing.aliyuncs.com/v2020GPUTraces"
MIRROR_REPO="https://github.com/qzweng/clusterdata-cluster-trace-gpu-v2020-data"

TABLES=(
  pai_job_table
  pai_task_table
  pai_instance_table
  pai_sensor_table
  pai_group_tag_table
  pai_machine_spec
  pai_machine_metric
)

# 미러 저장소 README 에 고시된 sha256 (tar.gz 기준)
declare -A SHA256=(
  [pai_group_tag_table]=722fef30b7fb7aa50dabd79155614b5423a9d65cf45a9b26c590d57725423a14
  [pai_instance_table]=1bf1e423a7ce3f8d086699801c362fd56a7182abdb234139e5ebbed97995ca06
  [pai_job_table]=5aad7f7caac501136d14ed6a48e40546f825d7b0617a3a4f337e2348fe0a6cb0
  [pai_machine_metric]=53ad917193d3b1dd0f3055e723148b1f36c2f81789b014ea2930a7875892eef5
  [pai_machine_spec]=cc0d38a4045af1b1af8179de8b1b54b1ddd995e6160d6d061a6b1000f1276c2d
  [pai_sensor_table]=9a0b82e8bdf3949281e4ba1423d9b4b34847e52799eecb138966de46da69c7a0
  [pai_task_table]=cd1d6dc3215d2a8607ccf6b6dd952b5db776df86926c73259fea7c1499ac40e5
)

log() { printf '[fetch_data] %s\n' "$*" >&2; }

all_present() {
  local t
  for t in "${TABLES[@]}"; do
    [[ -s "$RAW_DIR/$t.csv" ]] || return 1
  done
  return 0
}

verify() {          # verify <table> <tar.gz path>
  local table="$1" path="$2" expected="${SHA256[$1]}" actual
  actual="$(sha256sum "$path" | cut -d' ' -f1)"
  if [[ "$actual" != "$expected" ]]; then
    log "FAIL 체크섬 불일치: $table"
    log "  expected=$expected"
    log "  actual  =$actual"
    return 1
  fi
  log "OK   체크섬 $table"
}

fetch_oss() {
  local t
  for t in "${TABLES[@]}"; do
    log "OSS 다운로드: $t"
    curl -fsSL --max-time 900 -o "$WORK_DIR/$t.tar.gz" "$OSS_BASE/$t.tar.gz"
  done
}

fetch_mirror() {
  local clone="$WORK_DIR/mirror" t
  if [[ ! -d "$clone/.git" ]]; then
    log "미러 클론: $MIRROR_REPO"
    GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 "$MIRROR_REPO" "$clone"
  else
    log "미러 이미 존재, 재사용"
  fi
  for t in "${TABLES[@]}"; do
    if compgen -G "$clone/$t.tar.gz.part*" >/dev/null; then
      log "분할 병합: $t"
      cat "$clone/$t.tar.gz.part"* > "$WORK_DIR/$t.tar.gz"
    elif [[ -f "$clone/$t.tar.gz" ]]; then
      cp "$clone/$t.tar.gz" "$WORK_DIR/$t.tar.gz"
    else
      log "FAIL 미러에 $t 없음"
      return 1
    fi
  done
}

main() {
  if all_present; then
    log "이미 추출 완료 — 건너뜀 ($RAW_DIR)"
    return 0
  fi

  mkdir -p "$RAW_DIR" "$WORK_DIR"

  case "$SOURCE" in
    oss)    fetch_oss ;;
    mirror) fetch_mirror ;;
    auto)
      if fetch_oss; then
        log "OSS 경로 성공"
      else
        log "OSS 실패 — 미러로 전환"
        fetch_mirror
      fi
      ;;
    *) log "알 수 없는 SOURCE=$SOURCE"; return 2 ;;
  esac

  local t
  for t in "${TABLES[@]}"; do
    verify "$t" "$WORK_DIR/$t.tar.gz"
    log "추출: $t"
    tar -xzf "$WORK_DIR/$t.tar.gz" -C "$RAW_DIR"
    rm -f "$WORK_DIR/$t.tar.gz"          # 디스크 절약: 추출 직후 제거
  done

  log "완료 → $RAW_DIR"
  ls -la "$RAW_DIR"
}

main "$@"
