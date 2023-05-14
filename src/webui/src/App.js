// This is the main app for diplaying fuzzing progress
// Copyright (c) 2019 Robert Bosch GmbH
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.
import { useState, useEffect, useLayoutEffect, useRef } from "react";
import {
  INITIAL_VALUE,
  ReactSVGPanZoom,
  TOOL_NONE,
  fitSelection,
  zoomOnViewerCenter,
  fitToViewer,
} from "react-svg-pan-zoom";
import SVG from "./components/SVG";
import mqtt from "mqtt";
import { uint8array_to_string } from "./util";
import Breakpoints from "./components/Breakpoints";
import FuzzerStats from "./components/FuzzerStats";
import { ReactSvgPanZoomLoader } from "react-svg-pan-zoom-loader";
import { SvgLoader, SvgProxy } from "react-svgmt";
import { useWindowSize } from "@react-hook/window-size";

const mqtt_broker_URI = "http://127.0.0.1:9001";

export default function App() {
  const [mqtt_client, set_mqtt_client] = useState(null);
  // 'Connected', 'Reconnecting', 'Disconnected', or 'Connection Error'
  const [mqtt_connection_status, set_mqtt_connection_status] = useState(null);

  const [cfg_svg, set_cfg_svg] = useState(null);
  const [coverage_over_time_svg, set_coverage_over_time_svg] = useState(null);

  const [fuzzer_stats, set_fuzzer_stats] = useState({ coverage: 0, runs: 0 });

  const [breakpoints, set_breakpoints] = useState([]);

  const [value, setValue] = useState(INITIAL_VALUE);
  const [tool, setTool] = useState(TOOL_NONE);
  const [covValue, setCovValue] = useState(INITIAL_VALUE);
  const [covTool, setCovTool] = useState(TOOL_NONE);

  useEffect(() => {
    const client = mqtt.connect(mqtt_broker_URI, {
      rejectUnauthorized: false,
      // If a connection breaks and successfully reconnects, subscribe to the
      // same topics from the previous connection again
      resubscribe: true,
    });

    if (mqtt_client != null) {
      // Cleanup the previous MQTT client connection
      mqtt_client.end();
    }

    set_mqtt_client(client);
  }, []);

  // Callbacks for when MQTT events occur (e.g. a new message from the MQTT
  // broker arrived or a reconnect occured).
  useEffect(() => {
    // Return if the App did not connect to the MQTT broker yet.
    if (mqtt_client == null) return;

    // On successful (re)connect.
    mqtt_client.on("connect", () => {
      console.log("MQTT connection status: Connected.");
      set_mqtt_connection_status("Connected");

      subscribe_to_topics();
    });

    // On receiving a publish message.
    mqtt_client.on("message", (topic, message) => {
      on_message_received(topic, message);
    });

    // When a reconnection starts (and has not finish yet).
    mqtt_client.on("reconnect", () => {
      console.log("MQTT connection status: Reconnecting.");
      set_mqtt_connection_status("Reconnecting");
    });

    // On receiving a disconnect packet from the MQTT Broker (This is a
    // MQTT 5.0 feature).
    mqtt_client.on("disconnect", () => {
      console.log("MQTT connection status: Disconnected.");
      set_mqtt_connection_status("Disconnected");
    });

    // On parsing errors or when the client cannot connect to the MQTT broker.
    mqtt_client.on("error", (error) => {
      console.error("MQTT Connection error:", error);
      set_mqtt_connection_status("Connection Error");
      if (mqtt_client != null) {
        mqtt_client.end();
      }
    });
  }, [mqtt_client]); // eslint-disable-line react-hooks/exhaustive-deps

  const subscribe_to_topics = () => {
    mqtt_client.subscribe("cfg", { qos: 2 }, (error) => {
      if (!error) return;
      console.error("Subscribe to topic 'test/hello' error:", error);
    });

    mqtt_client.subscribe("fuzzer_stats", { qos: 2 }, (error) => {
      if (!error) return;
      console.error("Subscribe to topic 'fuzzer_stats' error:", error);
    });

    mqtt_client.subscribe("coverage_over_time", { qos: 2 }, (error) => {
      if (!error) return;
      console.error("Subscribe to topic 'coverage_over_time' error:", error);
    });

    mqtt_client.subscribe("breakpoints", { qos: 2 }, (error) => {
      if (!error) return;
      console.error("Subscribe to topic 'breakpoints' error:", error);
    });
  };

  // On receiving a MQTT message from the MQTT broker, process this message
  // depending on the topic.
  const on_message_received = (topic, message_uint8) => {
    // Received 'message_uint8' messages have the type Uint8Array.
    const message = uint8array_to_string(message_uint8);

    if (topic === "cfg") {
      set_cfg_svg(message);
    } else if (topic == "fuzzer_stats") {
      set_fuzzer_stats(JSON.parse(message));
    } else if (topic == "coverage_over_time") {
      set_coverage_over_time_svg(message);
    } else if (topic == "breakpoints") {
      set_breakpoints(JSON.parse(message));
    }
  };

  const mqtt_publish_message = (topic, message) => {
    mqtt_client.publish(topic, message, { qos: 2 }, (error) => {
      if (!error) return;
      console.error(
        "Failed to publish '" + message + "' to topic '" + topic + "'"
      );
    });
  };

  const [width, height] = useWindowSize({
    initialWidth: 400,
    initialHeight: 400,
  });

  return (
    <div className="flex min-h-screen">
      <div className="w-1/6 sticky top-0 h-full space-y-24 z-50">
        <Breakpoints breakpoints={breakpoints} />
        <FuzzerStats fuzzer_stats={fuzzer_stats} />
      </div>
      <div className="w-4/5 h-full flex flex-col">
        <SVG
          svg_string={cfg_svg}
          render={(content) => (
            <ReactSVGPanZoom
              scaleFactorOnWheel={2}
              miniatureProps={{ position: "right", width: 150, height: 300 }}
              defaultTool="pan"
              detectAutoPan={false}
              tool={tool}
              onChangeTool={setTool}
              value={value}
              onChangeValue={setValue}
              width={(width * 4) / 5}
              height={height}
              background="#ffffff"
            >
              <svg width={10000} height={15000}>
                {content}
              </svg>
            </ReactSVGPanZoom>
          )}
        />
      </div>
    </div>
  );
}
