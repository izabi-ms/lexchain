import React from "react";
import { Card, Button } from "react-bootstrap";

function HistoryItem({ item, onSelect }) {
  return (
    <Card className="mb-3 silky-card fadein" style={{ borderLeft: "4px solid #203778" }}>
      <Card.Body>
        <Card.Title className="fw-semibold">{item.document_type}</Card.Title>
        <Card.Text>
          <b>Client Data:</b> {item.client_data}<br/>
          <b>Tx Hash:</b> {item.transaction_hash || "-"}<br/>
          <b>Doc Hash:</b> {item.document_hash || "-"}<br/>
          <b>Date:</b> {item.timestamp ? new Date(item.timestamp).toLocaleString() : "-"}<br/>
          {item.has_pdf && (
            <a
              href={`${process.env.REACT_APP_BACKEND_URL || "http://localhost:8000"}/pdf/${item.document_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-sm btn-outline-success mt-2"
            >
              Download PDF
            </a>
          )}
        </Card.Text>
        <Button variant="outline-primary" className="silky-btn silky-btn-outline" onClick={onSelect}>View Document</Button>
      </Card.Body>
    </Card>
  );
}
export default HistoryItem;
