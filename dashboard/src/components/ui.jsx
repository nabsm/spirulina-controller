export function Pill({ children, tone = "neutral" }) {
    const base =
      "inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold";
    const map = {
      neutral: "bg-surface text-text2",
      ok: "bg-green-900/50 text-green-400",
      warn: "bg-yellow-900/50 text-yellow-400",
      bad: "bg-red-900/50 text-red-400",
      primary: "bg-primary text-white",
      accent: "bg-accent/20 text-accent",
    };
    return <span className={`${base} ${map[tone] || map.neutral}`}>{children}</span>;
  }

  export function Card({ title, children, right }) {
    return (
      <div className="relative z-0 rounded-xl2 bg-panel shadow-soft border border-line p-4 overflow-hidden">
        <div className="flex items-start justify-between gap-3 relative z-10">
          <div className="text-sm font-semibold text-text2">{title}</div>
          {right}
        </div>
        <div className="mt-2 relative z-10">{children}</div>
      </div>
    );
  }


  export function Button({ children, onClick, variant = "primary", disabled }) {
    const base =
      `
      relative inline-flex items-center justify-center
      rounded-xl2 px-3 py-2 text-sm font-semibold
      border transition-all duration-150
      hover:cursor-pointer
      focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-panel
      active:translate-y-[1px] active:shadow-inner
      `;

    const map = {
      primary: `
        bg-primary text-white border-primary
        hover:bg-primaryHover hover:shadow-soft
        focus-visible:ring-primary
        disabled:bg-surface disabled:border-surface disabled:text-text2
        disabled:cursor-not-allowed disabled:shadow-none disabled:translate-y-0
      `,
      ghost: `
        bg-surface text-text border-line
        hover:bg-surfaceHover hover:shadow-soft
        active:bg-surfaceHover
        focus-visible:ring-primary
        disabled:bg-surface disabled:border-surface disabled:text-text2
        disabled:cursor-not-allowed disabled:shadow-none disabled:translate-y-0
      `,
      accent: `
        bg-accent text-panel border-accent
        hover:bg-accentHover hover:shadow-soft
        focus-visible:ring-accent
        disabled:bg-surface disabled:text-text2 disabled:border-surface
        disabled:cursor-not-allowed disabled:shadow-none disabled:translate-y-0
      `,
      danger: `
        bg-red-600 text-white border-red-600
        hover:bg-red-700 hover:shadow-soft
        focus-visible:ring-red-600
        disabled:bg-red-900 disabled:border-red-900 disabled:text-red-300
        disabled:cursor-not-allowed disabled:shadow-none disabled:translate-y-0
      `,
    };

    return (
      <button
        type="button"
        className={`${base} ${map[variant]}`}
        disabled={!!disabled}
        onClick={onClick}
      >
        {children}
      </button>
    );
  }

  export function Input({ value, onChange, placeholder, type = "text", step }) {
    return (
      <input
        className="w-full rounded-xl2 border border-line bg-surface px-3 py-2 text-sm text-text placeholder-text2 outline-none focus:border-primary focus:ring-1 focus:ring-primary/30"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        type={type}
        step={type === "number" ? (step ?? "any") : undefined}
      />
    );
  }

  export function Select({ value, onChange, options }) {
    return (
      <select
        className="w-full rounded-xl2 border border-line bg-surface px-3 py-2 text-sm text-text outline-none focus:border-primary focus:ring-1 focus:ring-primary/30"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    );
  }

  export function ToggleSwitch({ checked, onChange, disabled, labelOn = "On", labelOff = "Off" }) {
    return (
      <button
        type="button"
        disabled={!!disabled}
        onClick={() => onChange(!checked)}
        className={`
          relative inline-flex items-center justify-between gap-3
          w-full rounded-xl2 border px-3 py-2 text-sm font-semibold
          transition-all duration-150
          focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-panel
          active:translate-y-[1px]
          ${disabled ? "cursor-not-allowed opacity-60" : "hover:shadow-soft hover:cursor-pointer"}
          ${checked
            ? "bg-primary text-white border-primary active:bg-primaryHover"
            : "bg-surface text-text border-line hover:bg-surfaceHover active:bg-surfaceHover"}
        `}
      >
        <span className="flex-1 text-left select-none truncate">
            {checked ? labelOn : labelOff}
        </span>

        <span
          className={`
            relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors
            ${checked ? "bg-accent" : "bg-line"}
          `}
        >
          <span
            className={`
              inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform
              ${checked ? "translate-x-5" : "translate-x-0.5"}
            `}
          />
        </span>
      </button>
    );
  }

  export function TwoWayToggle({ value, onChange, disabled, leftLabel = "OFF", rightLabel = "ON" }) {
    return (
      <div
        className={`
          grid grid-cols-2 gap-1
          ${disabled ? "opacity-60 pointer-events-none" : ""}
        `}
      >
        <button
          type="button"
          onClick={() => onChange(false)}
          className={`
            rounded-xl2 border px-3 py-2 text-sm font-semibold transition-all duration-150
            focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-panel
            active:translate-y-[1px] active:shadow-inner
            ${value === false ? "bg-primary text-white border-primary" : "bg-surface text-text border-line hover:bg-surfaceHover hover:shadow-soft active:bg-surfaceHover"}
          `}
        >
          {leftLabel}
        </button>

        <button
          type="button"
          onClick={() => onChange(true)}
          className={`
            rounded-xl2 border px-3 py-2 text-sm font-semibold transition-all duration-150
            focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-panel
            active:translate-y-[1px] active:shadow-inner
            ${value === true ? "bg-accent text-panel border-accent" : "bg-surface text-text border-line hover:bg-surfaceHover hover:shadow-soft active:bg-surfaceHover"}
          `}
        >
          {rightLabel}
        </button>
      </div>
    );
  }

  export function Drawer({ open, onClose, title, children }) {
  return (
    <>
      {/* Overlay */}
      <div
        className={`fixed inset-0 z-40 bg-black/40 transition-opacity duration-200 ${open ? "opacity-100" : "opacity-0 pointer-events-none"}`}
        onClick={onClose}
      />
      {/* Panel */}
      <div
        className={`fixed top-0 right-0 z-50 h-full w-full max-w-md bg-panel shadow-soft border-l border-line
          transform transition-transform duration-200 ease-in-out
          ${open ? "translate-x-0" : "translate-x-full"}`}
      >
        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <div className="text-sm font-semibold text-text">{title}</div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl2 border border-line bg-surface px-3 py-1 text-sm text-text2 hover:bg-surfaceHover hover:shadow-soft"
          >
            Close
          </button>
        </div>
        <div className="overflow-y-auto p-4" style={{ maxHeight: "calc(100vh - 56px)" }}>
          {children}
        </div>
      </div>
    </>
  );
}

export function TriToggle({ value, onChange, disabled, labels }) {
    const opts = labels || [
      { value: "off", label: "FORCE OFF" },
      { value: "auto", label: "AUTO" },
      { value: "on", label: "FORCE ON" },
    ];

    function selectedStyle(v) {
      if (v === "auto") return "bg-primary text-white border-primary";
      if (v === "on") return "bg-accent text-panel border-accent";
      return "bg-red-900/50 text-red-400 border-red-500";
    }

    return (
      <div className={`grid grid-cols-3 gap-1 ${disabled ? "opacity-60 pointer-events-none" : ""}`}>
        {opts.map((o) => (
          <button
            key={o.value}
            type="button"
            onClick={() => onChange(o.value)}
            className={`
              rounded-xl2 border px-3 py-2 text-xs font-semibold transition-all duration-150
              focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-panel
              active:translate-y-[1px] active:shadow-inner
              ${value === o.value
                ? selectedStyle(o.value)
                : "bg-surface text-text2 border-line hover:bg-surfaceHover hover:shadow-soft active:bg-surfaceHover"}
            `}
          >
            {o.label}
          </button>
        ))}
      </div>
    );
  }
