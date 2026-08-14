import React, { useState } from 'react';
import './TryModel.css';

export default function TryModel() {
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState({
    grade: 'M40',
    stdDev: 5,

    // INR/kg
    cementINR: 5.7, waterINR: 0.05, fineINR: 0.3, coarseINR: 0.45,
    flyAshINR: 8, silicaINR: 32, slagINR: 2, plasticINR: 38,

    // CO₂/kg
    cementCO2: 0.9, waterCO2: 0, fineCO2: 0.003, coarseCO2: 0.005,
    flyAshCO2: 0.2, silicaCO2: 0.01, slagCO2: 0.15, plasticCO2: 0.1,

    // kg/m³
    cementKG: 3150, waterKG: 1000, fineKG: 2600, coarseKG: 2650,
    flyAshKG: 2200, silicaKG: 2200, slagKG: 2900, plasticKG: 1100,
  });

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError('');
    try {
      const response = await fetch('http://127.0.0.1:5000/api/optimizations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || 'Unable to run the optimization.');
      setResult(body);
    } catch (submissionError) {
      setError(submissionError.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const costFields = [
    ['cementINR', 'Cement'], ['waterINR', 'Water'], ['fineINR', 'Fine Aggregate'],
    ['coarseINR', 'Coarse Aggregate'], ['flyAshINR', 'Fly Ash'], ['silicaINR', 'Silica'],
    ['slagINR', 'Slag'], ['plasticINR', 'Plasticizer'],
  ];
  const emissionsFields = [
    ['cementCO2', 'Cement'], ['waterCO2', 'Water'], ['fineCO2', 'Fine Aggregate'],
    ['coarseCO2', 'Coarse Aggregate'], ['flyAshCO2', 'Fly Ash'], ['silicaCO2', 'Silica'],
    ['slagCO2', 'Slag'], ['plasticCO2', 'Plasticizer'],
  ];
  const densityFields = [
    ['cementKG', 'Cement'], ['waterKG', 'Water'], ['fineKG', 'Fine Aggregate'],
    ['coarseKG', 'Coarse Aggregate'], ['flyAshKG', 'Fly Ash'], ['silicaKG', 'Silica'],
    ['slagKG', 'Slag'], ['plasticKG', 'Plasticizer'],
  ];

  return (
    <div className="trymodel">
      <h2>🧱 Concrete Mix Design Optimizer</h2>

      <div className="input-section">
        <label>
          Concrete Grade:
          <select name="grade" value={form.grade} onChange={handleChange}>
            <option value="M40">M40</option>
            <option value="M50">M50</option>
            <option value="M60">M60</option>
            <option value="M70">M70</option>
            <option value="M80">M80</option>
            <option value="M90">M90</option>
            <option value="M100">M100</option>
            <option value="M110">M110</option>
            <option value="M120">M120</option>
          </select>
        </label>

        <label>
          Standard Deviation:
          <input type="number" name="stdDev" value={form.stdDev} onChange={handleChange} />
        </label>
      </div>
      <div className="inputform">
      <h4>💰 Cost (INR/kg)</h4>
      <div className="grid">
        {costFields.map(([key, label]) => (
          <label key={key}>{label}
            <input type="number" name={key} value={form[key]} onChange={handleChange} />
          </label>
        ))}
      </div>

      <h4>🌍 Emissions (kg CO₂/kg)</h4>
      <div className="grid">
        {emissionsFields.map(([key, label]) => (
          <label key={key}>{label}
            <input className="default-input" type="number" name={key} value={form[key]} onChange={handleChange} />
          </label>
        ))}
      </div>

      <h4>⚖️ Material Density (kg/m³)</h4>
      <div className="grid">
        {densityFields.map(([key, label]) => (
          <label key={key}>{label}
            <input className="default-input" type="number" name={key} value={form[key]} onChange={handleChange} />
          </label>
        ))}
      </div>
      </div>
      <button className="submit-btn" onClick={handleSubmit} disabled={isSubmitting}>
        Run Optimization 🚀
      </button>
      {error && <p className="form-error">{error}</p>}

      {/* Result Table Placeholder */}
      <h3>Top 10 Mix Designs</h3>
      <div className="results-table">
        {!result && 'Run an optimization to see up to 10 Pareto-optimal mix designs.'}
        {result && <>
          <p>Target strength: {result.targetStrength} MPa</p>
          <div className="table-scroll">
            <table>
              <thead><tr><th>Mix</th><th>Strength (MPa)</th><th>Cost (INR/m³)</th><th>CO₂ (kg/m³)</th></tr></thead>
              <tbody>{result.solutions.map((solution, index) => (
                <tr key={index}>
                  <td>{index + 1}</td><td>{solution.strength}</td><td>{solution.cost}</td><td>{solution.co2}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </>}
      </div>

      {/* Pareto Plot Placeholder */}
      <h3>📊 Pareto Front</h3>
      <div className="pareto-plot">[Plot will go here]</div>
    </div>
  );
}
