import React from "react";
import ReactDOM from "react-dom/client";
import "./styles.css";
import { PhoneApp } from "./phone/PhoneApp";
import { HostApp } from "./host/HostApp";

const isPhone = new URLSearchParams(window.location.search).get("mode") === "phone";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>{isPhone ? <PhoneApp /> : <HostApp />}</React.StrictMode>,
);
