type BrandProps = {
  size?: number;
  wordmark?: boolean;
  light?: boolean;
};

export function Brand({ size = 32, wordmark = true, light = false }: BrandProps) {
  return (
    <span className={`brand${light ? " light" : ""}`}>
      <img src="/icon.svg" alt="" width={size} height={size} />
      {wordmark && <span className="brand-name">Ihtama</span>}
    </span>
  );
}
