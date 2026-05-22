import { useEffect, useState } from "react";

export default function Ranking() {
  const [players, setPlayers] = useState([]);
  const [search, setSearch] = useState("");
  const [mode, setMode] = useState("std");
  const [topOnly, setTopOnly] = useState(false);

  useEffect(() => {
    fetch(`http://127.0.0.1:8000/ranking/${mode}`)
      .then(res => res.json())
      .then(data => setPlayers(data));
  }, [mode]);

  const filtered = players
    .filter(p =>
      p.name.toLowerCase().includes(search.toLowerCase())
    );

  const displayed = topOnly ? filtered.slice(0, 10) : filtered;

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>🏆 Ranking FPBX</h2>

      {/* CONTROLES */}
      <div style={styles.controls}>
        <input
          placeholder="Buscar jogador..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={styles.input}
        />

        <div style={styles.buttons}>
          <button
            onClick={() => setMode("std")}
            style={mode === "std" ? styles.activeBtn : styles.btn}
          >
            STD
          </button>

          <button
            onClick={() => setMode("rapid")}
            style={mode === "rapid" ? styles.activeBtn : styles.btn}
          >
            RAPID
          </button>

          <button
            onClick={() => setMode("blitz")}
            style={mode === "blitz" ? styles.activeBtn : styles.btn}
          >
            BLITZ
          </button>

          <button
            onClick={() => setTopOnly(!topOnly)}
            style={topOnly ? styles.activeBtn : styles.btn}
          >
            {topOnly ? "MOSTRAR TODOS" : "TOP 10"}
          </button>
        </div>
      </div>

      {/* TABELA */}
      <table style={styles.table}>
        <thead>
          <tr style={styles.headRow}>
            <th style={styles.th}>Pos</th>
            <th style={styles.th}>Nome</th>
            <th style={styles.th}>Rating</th>
          </tr>
        </thead>

        <tbody>
          {displayed.map((p, i) => (
            <tr key={p.id} style={styles.row}>
              <td style={styles.td}>#{i + 1}</td>
              <td style={styles.td}>{p.name}</td>
              <td style={styles.td}>{p.rating}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
const styles = {
  container: {
    padding: 20,
    fontFamily: "Arial, sans-serif",
    maxWidth: 900,
    margin: "0 auto"
  },

  title: {
    textAlign: "center",
    marginBottom: 20
  },

  controls: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
    marginBottom: 20
  },

  input: {
    padding: 10,
    border: "1px solid #ccc",
    borderRadius: 6,
    width: "100%",
    maxWidth: 300
  },

  buttons: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap"
  },

  btn: {
    padding: "8px 12px",
    border: "1px solid #ccc",
    background: "#f5f5f5",
    cursor: "pointer",
    borderRadius: 6
  },

  activeBtn: {
    padding: "8px 12px",
    border: "1px solid #000",
    background: "#000",
    color: "#fff",
    cursor: "pointer",
    borderRadius: 6
  },

  table: {
    width: "100%",
    borderCollapse: "collapse"
  },

  headRow: {
    background: "#eee"
  },

  row: {
    borderBottom: "1px solid #ddd"
  },

  th: {
    textAlign: "left",
    padding: 10
  },

  td: {
    padding: 10
  }
};