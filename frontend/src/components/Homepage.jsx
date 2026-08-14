import React from 'react';
import './Homepage.css';
import { useNavigate } from 'react-router-dom';

export default function Homepage() {
  const navigate = useNavigate();

  return (
    <div className="home">
      <div className="heading"><h1>Optimal Mix</h1></div>
      <div className="paragraph">
        <p>Optimal Mix is a tool designed to help you find the best mix of stocks for your portfolio.</p>
        <p>It uses the Markowitz Mean-Variance Optimization algorithm to find the optimal weights for each stock in your portfolio.</p>
      </div>
      <div className="btn">
        <button onClick={() => navigate('/trymodel')}>Try Model</button>
      </div>
    </div>
  );
}
