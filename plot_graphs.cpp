#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <filesystem>
#include <cstdlib>
#include <cmath>
#include <algorithm>
#include <regex>
#include <iomanip>

namespace fs = std::filesystem;

struct DataPoint {
    double eight_over_a;
    double b_value;
    double c_value;
    double sender_bitrate;
    double median_latency;
    double linear_r_squared;
    double quadratic_r_squared;
    std::string time_label;
    int time_minutes;
    std::string filename;
    bool valid_a;
    bool valid_b;
    bool valid_c;
};

// Extract nested quadratic 'a' coefficient
double extractQuadraticA(const std::string& json) {
    size_t quadPos = json.find("\"quadratic\"");
    if (quadPos == std::string::npos) return 0.0;

    size_t coeffPos = json.find("\"coefficients\"", quadPos);
    if (coeffPos == std::string::npos) return 0.0;

    size_t aPos = json.find("\"a\"", coeffPos);
    if (aPos == std::string::npos) return 0.0;

    size_t nextSection = json.find("\"r_squared\"", coeffPos);
    if (nextSection != std::string::npos && aPos > nextSection) return 0.0;

    size_t colonPos = json.find(":", aPos);
    if (colonPos == std::string::npos) return 0.0;

    size_t pos = colonPos + 1;
    while (pos < json.length() && (json[pos] == ' ' || json[pos] == '\n' || json[pos] == '\t')) {
        pos++;
    }

    size_t end = pos;
    while (end < json.length() && (isdigit(json[end]) || json[end] == '.' ||
           json[end] == '-' || json[end] == '+' || json[end] == 'e' || json[end] == 'E')) {
        end++;
    }

    std::string numStr = json.substr(pos, end - pos);
    return std::stod(numStr);
}

// Extract nested quadratic 'b' coefficient
double extractQuadraticB(const std::string& json) {
    size_t quadPos = json.find("\"quadratic\"");
    if (quadPos == std::string::npos) return 0.0;

    size_t coeffPos = json.find("\"coefficients\"", quadPos);
    if (coeffPos == std::string::npos) return 0.0;

    size_t bPos = json.find("\"b\"", coeffPos);
    if (bPos == std::string::npos) return 0.0;

    size_t nextSection = json.find("\"r_squared\"", coeffPos);
    if (nextSection != std::string::npos && bPos > nextSection) return 0.0;

    size_t colonPos = json.find(":", bPos);
    if (colonPos == std::string::npos) return 0.0;

    size_t pos = colonPos + 1;
    while (pos < json.length() && (json[pos] == ' ' || json[pos] == '\n' || json[pos] == '\t')) {
        pos++;
    }

    size_t end = pos;
    while (end < json.length() && (isdigit(json[end]) || json[end] == '.' ||
           json[end] == '-' || json[end] == '+' || json[end] == 'e' || json[end] == 'E')) {
        end++;
    }

    std::string numStr = json.substr(pos, end - pos);
    return std::stod(numStr);
}

// Extract quadratic 'c' coefficient (y-intercept)
double extractQuadraticC(const std::string& json) {
    size_t quadPos = json.find("\"quadratic\"");
    if (quadPos == std::string::npos) return 0.0;

    size_t coeffPos = json.find("\"coefficients\"", quadPos);
    if (coeffPos == std::string::npos) return 0.0;

    size_t cPos = json.find("\"c\"", coeffPos);
    if (cPos == std::string::npos) return 0.0;

    size_t nextSection = json.find("\"r_squared\"", coeffPos);
    if (nextSection != std::string::npos && cPos > nextSection) return 0.0;

    size_t colonPos = json.find(":", cPos);
    if (colonPos == std::string::npos) return 0.0;

    size_t pos = colonPos + 1;
    while (pos < json.length() && (json[pos] == ' ' || json[pos] == '\n' || json[pos] == '\t')) {
        pos++;
    }

    size_t end = pos;
    while (end < json.length() && (isdigit(json[end]) || json[end] == '.' ||
           json[end] == '-' || json[end] == '+' || json[end] == 'e' || json[end] == 'E')) {
        end++;
    }

    std::string numStr = json.substr(pos, end - pos);
    return std::stod(numStr);
}

// Extract linear r_squared from JSON
double extractLinearRSquared(const std::string& json) {
    size_t linPos = json.find("\"linear\"");
    if (linPos == std::string::npos) return 0.0;

    size_t rPos = json.find("\"r_squared\"", linPos);
    if (rPos == std::string::npos) return 0.0;

    // Make sure we're in the linear section, not quadratic
    size_t quadPos = json.find("\"quadratic\"", linPos);
    if (quadPos != std::string::npos && rPos > quadPos) return 0.0;

    size_t colonPos = json.find(":", rPos);
    if (colonPos == std::string::npos) return 0.0;

    size_t pos = colonPos + 1;
    while (pos < json.length() && (json[pos] == ' ' || json[pos] == '\n' || json[pos] == '\t')) {
        pos++;
    }

    size_t end = pos;
    while (end < json.length() && (isdigit(json[end]) || json[end] == '.' ||
           json[end] == '-' || json[end] == '+' || json[end] == 'e' || json[end] == 'E')) {
        end++;
    }

    std::string numStr = json.substr(pos, end - pos);
    return std::stod(numStr);
}

// Extract quadratic r_squared from JSON
double extractQuadraticRSquared(const std::string& json) {
    size_t quadPos = json.find("\"quadratic\"");
    if (quadPos == std::string::npos) return 0.0;

    size_t rPos = json.find("\"r_squared\"", quadPos);
    if (rPos == std::string::npos) return 0.0;

    size_t colonPos = json.find(":", rPos);
    if (colonPos == std::string::npos) return 0.0;

    size_t pos = colonPos + 1;
    while (pos < json.length() && (json[pos] == ' ' || json[pos] == '\n' || json[pos] == '\t')) {
        pos++;
    }

    size_t end = pos;
    while (end < json.length() && (isdigit(json[end]) || json[end] == '.' ||
           json[end] == '-' || json[end] == '+' || json[end] == 'e' || json[end] == 'E')) {
        end++;
    }

    std::string numStr = json.substr(pos, end - pos);
    return std::stod(numStr);
}

// Extract median_latency_ms from JSON
double extractMedianLatency(const std::string& json) {
    size_t pos = json.find("\"median_latency_ms\"");
    if (pos == std::string::npos) return 0.0;

    pos = json.find(":", pos);
    if (pos == std::string::npos) return 0.0;

    pos++;
    while (pos < json.length() && (json[pos] == ' ' || json[pos] == '\n' || json[pos] == '\t')) {
        pos++;
    }

    size_t end = pos;
    while (end < json.length() && (isdigit(json[end]) || json[end] == '.' ||
           json[end] == '-' || json[end] == '+' || json[end] == 'e' || json[end] == 'E')) {
        end++;
    }

    std::string numStr = json.substr(pos, end - pos);
    return std::stod(numStr);
}

// Extract sender_bitrate from JSON
double extractSenderBitrate(const std::string& json) {
    size_t pos = json.find("\"sender_bitrate\"");
    if (pos == std::string::npos) return 0.0;

    pos = json.find(":", pos);
    if (pos == std::string::npos) return 0.0;

    pos++;
    while (pos < json.length() && (json[pos] == ' ' || json[pos] == '\n' || json[pos] == '\t')) {
        pos++;
    }

    size_t end = pos;
    while (end < json.length() && (isdigit(json[end]) || json[end] == '.' ||
           json[end] == '-' || json[end] == '+' || json[end] == 'e' || json[end] == 'E')) {
        end++;
    }

    std::string numStr = json.substr(pos, end - pos);
    return std::stod(numStr);
}

// Extract military time from filename like "scp_data_analyzed_0016.json" -> "00:16"
std::string extractTimeLabel(const std::string& filename) {
    std::regex timeRegex("_(\\d{4})\\.json$");
    std::smatch match;
    if (std::regex_search(filename, match, timeRegex)) {
        std::string timeStr = match[1].str();
        return timeStr.substr(0, 2) + ":" + timeStr.substr(2, 2);
    }
    return "00:00";
}

// Convert time label to minutes for sorting
int timeToMinutes(const std::string& timeLabel) {
    int hours = std::stoi(timeLabel.substr(0, 2));
    int minutes = std::stoi(timeLabel.substr(3, 2));
    return hours * 60 + minutes;
}

int main(int argc, char* argv[]) {
    std::string dataDir = "results/CronTab215";

    if (argc > 1) {
        dataDir = argv[1];
    }

    if (!fs::exists(dataDir)) {
        std::cerr << "Error: Directory '" << dataDir << "' not found.\n";
        return 1;
    }

    std::vector<DataPoint> allData;
    int totalFiles = 0;

    // Read only scp_data_analyzed_*.json files
    for (const auto& entry : fs::directory_iterator(dataDir)) {
        std::string filename = entry.path().filename().string();
        if (entry.path().extension() == ".json" && filename.find("scp_data_analyzed_") == 0) {
            totalFiles++;
            std::ifstream file(entry.path());
            if (!file.is_open()) {
                std::cerr << "Warning: Could not open " << entry.path() << "\n";
                continue;
            }

            std::stringstream buffer;
            buffer << file.rdbuf();
            std::string json = buffer.str();

            double a = extractQuadraticA(json);
            double b = extractQuadraticB(json);
            double c = extractQuadraticC(json);
            double senderBitrate = extractSenderBitrate(json);
            double medianLatency = extractMedianLatency(json);
            double linearRSq = extractLinearRSquared(json);
            double quadraticRSq = extractQuadraticRSquared(json);

            DataPoint dp;
            dp.sender_bitrate = senderBitrate;
            dp.median_latency = medianLatency;
            dp.linear_r_squared = linearRSq;
            dp.quadratic_r_squared = quadraticRSq;

            // Check validity for 'c' and convert to ms
            dp.valid_c = (std::isfinite(c));
            if (dp.valid_c) {
                dp.c_value = c * 1000.0;  // Convert seconds to ms
            }
            dp.filename = entry.path().filename().string();
            dp.time_label = extractTimeLabel(dp.filename);
            dp.time_minutes = timeToMinutes(dp.time_label);

            // Check validity for 'a'
            dp.valid_a = (a != 0.0 && std::isfinite(a));
            if (dp.valid_a) {
                // Convert to Mbits/sec: 8/a gives bits, divide by 1e6 for Mbits
                dp.eight_over_a = (8.0 / a) / 1e6;
                if (!std::isfinite(dp.eight_over_a)) {
                    dp.valid_a = false;
                }
            }

            // Check validity for 'b'
            dp.valid_b = (b != 0.0 && std::isfinite(b));
            if (dp.valid_b) {
                // Convert to ms/byte (multiply by 1000)
                dp.b_value = b * 1000.0;
            }

            allData.push_back(dp);
        }
    }

    // Sort by time
    std::sort(allData.begin(), allData.end(),
              [](const DataPoint& a, const DataPoint& b) {
                  return a.time_minutes < b.time_minutes;
              });

    // Filter data for each graph
    std::vector<DataPoint> aData, bData;
    for (const auto& dp : allData) {
        if (dp.valid_a) aData.push_back(dp);
        if (dp.valid_b) bData.push_back(dp);
    }

    std::cout << "Processed " << totalFiles << " files\n\n";

    // ========== Graph 1: 8/a vs Run Number ==========
    std::cout << "Graph 1: 8/a vs Run Number\n";
    std::cout << "  Valid data points: " << aData.size() << "\n";

    if (!aData.empty()) {
        std::ofstream dataFile("plot_data_a.tmp");
        for (size_t i = 0; i < aData.size(); i++) {
            dataFile << i << " " << aData[i].eight_over_a << "\n";
        }
        dataFile.close();

        std::ofstream gnuplotScript("plot_script_a.gp");
        gnuplotScript << "set terminal png size 1000,600 enhanced font 'Arial,11'\n";
        gnuplotScript << "set output '8avsRuntime.png'\n";
        gnuplotScript << "set title '8/a (data rate in Mbits/sec) vs Run Number'\n";
        gnuplotScript << "set xlabel 'Run Time (Military Time)'\n";
        gnuplotScript << "set ylabel '8/a (Mbits/sec)'\n";
        gnuplotScript << "set format y '%.4e'\n";
        gnuplotScript << "set grid\n";
        gnuplotScript << "set pointsize 1.5\n";
        gnuplotScript << "set xtics rotate by -45\n";

        gnuplotScript << "set xtics (";
        for (size_t i = 0; i < aData.size(); i++) {
            if (i > 0) gnuplotScript << ", ";
            gnuplotScript << "\"" << aData[i].time_label << "\" " << i;
        }
        gnuplotScript << ")\n";

        gnuplotScript << "set xrange [-0.5:" << (aData.size() - 0.5) << "]\n";
        gnuplotScript << "plot 'plot_data_a.tmp' using 1:2 with points pt 7 lc rgb 'blue' title 'Trials'\n";
        gnuplotScript.close();

        int result = system("gnuplot plot_script_a.gp");
        if (result == 0) {
            std::cout << "  Saved: 8avsRuntime.png\n";
            fs::remove("plot_data_a.tmp");
            fs::remove("plot_script_a.gp");
        } else {
            std::cerr << "  Error: gnuplot failed for 8/a graph\n";
        }
    }

    // ========== Graph 2: b vs Run Number ==========
    std::cout << "\nGraph 2: b vs Run Number\n";
    std::cout << "  Valid data points: " << bData.size() << "\n";

    if (!bData.empty()) {
        std::ofstream dataFile("plot_data_b.tmp");
        for (size_t i = 0; i < bData.size(); i++) {
            dataFile << i << " " << bData[i].b_value << "\n";
        }
        dataFile.close();

        std::ofstream gnuplotScript("plot_script_b.gp");
        gnuplotScript << "set terminal png size 1000,600 enhanced font 'Arial,11'\n";
        gnuplotScript << "set output 'bvsRuntime.png'\n";
        gnuplotScript << "set title 'b (ms/byte) vs runtime'\n";
        gnuplotScript << "set xlabel 'Run Time (Military Time)'\n";
        gnuplotScript << "set ylabel 'b (ms/byte)'\n";
        gnuplotScript << "set format y '%.4f'\n";
        gnuplotScript << "set grid\n";
        gnuplotScript << "set pointsize 1.5\n";
        gnuplotScript << "set xtics rotate by -45\n";

        gnuplotScript << "set xtics (";
        for (size_t i = 0; i < bData.size(); i++) {
            if (i > 0) gnuplotScript << ", ";
            gnuplotScript << "\"" << bData[i].time_label << "\" " << i;
        }
        gnuplotScript << ")\n";

        gnuplotScript << "set xrange [-0.5:" << (bData.size() - 0.5) << "]\n";
        gnuplotScript << "plot 'plot_data_b.tmp' using 1:2 with points pt 7 lc rgb 'blue' title 'Trials'\n";
        gnuplotScript.close();

        int result = system("gnuplot plot_script_b.gp");
        if (result == 0) {
            std::cout << "  Saved: bvsRuntime.png\n";
            fs::remove("plot_data_b.tmp");
            fs::remove("plot_script_b.gp");
        } else {
            std::cerr << "  Error: gnuplot failed for b graph\n";
        }
    }

    // ========== Graph 3: b vs Ping Latency with Linear Regression ==========
    std::cout << "\nGraph 3: b vs Ping Latency (with Linear Regression)\n";
    std::cout << "  Valid data points: " << bData.size() << "\n";

    if (!bData.empty()) {
        // Calculate linear regression: y = mx + c
        double sum_x = 0, sum_y = 0, sum_xy = 0, sum_x2 = 0;
        int n = bData.size();
        for (const auto& dp : bData) {
            sum_x += dp.median_latency;
            sum_y += dp.b_value;
            sum_xy += dp.median_latency * dp.b_value;
            sum_x2 += dp.median_latency * dp.median_latency;
        }
        double slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x);
        double intercept = (sum_y - slope * sum_x) / n;

        // Calculate R²
        double mean_y = sum_y / n;
        double ss_tot = 0, ss_res = 0;
        for (const auto& dp : bData) {
            double predicted = slope * dp.median_latency + intercept;
            ss_res += (dp.b_value - predicted) * (dp.b_value - predicted);
            ss_tot += (dp.b_value - mean_y) * (dp.b_value - mean_y);
        }
        double r_squared = 1.0 - (ss_res / ss_tot);

        std::cout << "  Linear fit: b = " << slope << " * latency + " << intercept << "\n";
        std::cout << "  R² = " << r_squared << "\n";

        std::ofstream dataFile("plot_data_scatter.tmp");
        for (size_t i = 0; i < bData.size(); i++) {
            dataFile << bData[i].median_latency << " " << bData[i].b_value << "\n";
        }
        dataFile.close();

        std::ofstream gnuplotScript("plot_script_scatter.gp");
        gnuplotScript << "set terminal png size 1000,600 enhanced font 'Arial,11'\n";
        gnuplotScript << "set output 'bvsPing_regression.png'\n";
        gnuplotScript << "set title 'b vs Ping Latency (R² = " << std::fixed << std::setprecision(4) << r_squared << ")'\n";
        gnuplotScript << "set xlabel 'Ping Latency (ms)'\n";
        gnuplotScript << "set ylabel 'b (ms/byte)'\n";
        gnuplotScript << "set format y '%.4f'\n";
        gnuplotScript << "set grid\n";
        gnuplotScript << "set pointsize 1.5\n";

        // Find min/max of b values for y-range
        double min_b = bData[0].b_value, max_b = bData[0].b_value;
        double min_lat = bData[0].median_latency, max_lat = bData[0].median_latency;
        for (const auto& dp : bData) {
            if (dp.b_value < min_b) min_b = dp.b_value;
            if (dp.b_value > max_b) max_b = dp.b_value;
            if (dp.median_latency < min_lat) min_lat = dp.median_latency;
            if (dp.median_latency > max_lat) max_lat = dp.median_latency;
        }
        double y_margin = (max_b - min_b) * 0.1;
        double x_margin = (max_lat - min_lat) * 0.1;
        gnuplotScript << "set yrange [" << (min_b - y_margin) << ":" << (max_b + y_margin) << "]\n";
        gnuplotScript << "set xrange [" << (min_lat - x_margin) << ":" << (max_lat + x_margin) << "]\n";

        // Write regression line data points
        std::ofstream regFile("plot_data_reg.tmp");
        regFile << min_lat << " " << (slope * min_lat + intercept) << "\n";
        regFile << max_lat << " " << (slope * max_lat + intercept) << "\n";
        regFile.close();

        gnuplotScript << "plot 'plot_data_scatter.tmp' using 1:2 with points pt 7 ps 1.5 lc rgb 'blue' title 'Trials', \\\n";
        gnuplotScript << "     'plot_data_reg.tmp' using 1:2 with lines lc rgb 'red' lw 2 title 'Linear Fit'\n";
        gnuplotScript.close();

        int result = system("gnuplot plot_script_scatter.gp");
        if (result == 0) {
            std::cout << "  Saved: bvsPing_regression.png\n";
            fs::remove("plot_data_scatter.tmp");
            fs::remove("plot_data_reg.tmp");
            fs::remove("plot_script_scatter.gp");
        } else {
            std::cerr << "  Error: gnuplot failed for regression plot\n";
        }
    }

    // ========== Graph 4: Dual-Axis Time Series (b and Ping Latency vs Time) ==========
    std::cout << "\nGraph 4: b and Ping Latency vs Time (Dual Axis)\n";
    std::cout << "  Valid data points: " << bData.size() << "\n";

    if (!bData.empty()) {
        std::ofstream dataFile("plot_data_dual.tmp");
        for (size_t i = 0; i < bData.size(); i++) {
            dataFile << i << " " << bData[i].b_value << " " << bData[i].median_latency << "\n";
        }
        dataFile.close();

        std::ofstream gnuplotScript("plot_script_dual.gp");
        gnuplotScript << "set terminal png size 1000,600 enhanced font 'Arial,11'\n";
        gnuplotScript << "set output 'bvsPing.png'\n";
        gnuplotScript << "set title 'b (Estimated) and Ping Latency vs Run Time'\n";
        gnuplotScript << "set xlabel 'Run Time (Military Time)'\n";
        gnuplotScript << "set ylabel 'b (ms/byte)' textcolor rgb 'blue'\n";
        gnuplotScript << "set y2label 'Ping Latency (ms)' textcolor rgb 'red'\n";
        gnuplotScript << "set ytics nomirror textcolor rgb 'blue'\n";
        gnuplotScript << "set y2tics nomirror textcolor rgb 'red'\n";
        gnuplotScript << "set format y '%.4f'\n";
        gnuplotScript << "set format y2 '%.1f'\n";
        gnuplotScript << "set grid\n";
        gnuplotScript << "set pointsize 1.5\n";
        gnuplotScript << "set xtics rotate by -45\n";

        gnuplotScript << "set xtics (";
        for (size_t i = 0; i < bData.size(); i++) {
            if (i > 0) gnuplotScript << ", ";
            gnuplotScript << "\"" << bData[i].time_label << "\" " << i;
        }
        gnuplotScript << ")\n";

        gnuplotScript << "set xrange [-0.5:" << (bData.size() - 0.5) << "]\n";
        gnuplotScript << "plot 'plot_data_dual.tmp' using 1:2 with linespoints pt 7 lc rgb 'blue' title 'b (left axis)', \\\n";
        gnuplotScript << "     'plot_data_dual.tmp' using 1:3 axes x1y2 with linespoints pt 5 lc rgb 'red' title 'Ping Latency (right axis)'\n";
        gnuplotScript.close();

        int result = system("gnuplot plot_script_dual.gp");
        if (result == 0) {
            std::cout << "  Saved: bvsPing.png\n";
            fs::remove("plot_data_dual.tmp");
            fs::remove("plot_script_dual.gp");
        } else {
            std::cerr << "  Error: gnuplot failed for dual-axis plot\n";
        }
    }

    // ========== Graph 5: 8/a vs iPerf3 Data Rate with Linear Regression ==========
    std::cout << "\nGraph 5: 8/a vs iPerf3 Data Rate (with Linear Regression)\n";
    std::cout << "  Valid data points: " << aData.size() << "\n";

    if (!aData.empty()) {
        // Calculate linear regression: y = mx + c
        double sum_x = 0, sum_y = 0, sum_xy = 0, sum_x2 = 0;
        int n = aData.size();
        for (const auto& dp : aData) {
            sum_x += dp.sender_bitrate;
            sum_y += dp.eight_over_a;
            sum_xy += dp.sender_bitrate * dp.eight_over_a;
            sum_x2 += dp.sender_bitrate * dp.sender_bitrate;
        }
        double slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x);
        double intercept = (sum_y - slope * sum_x) / n;

        // Calculate R²
        double mean_y = sum_y / n;
        double ss_tot = 0, ss_res = 0;
        for (const auto& dp : aData) {
            double predicted = slope * dp.sender_bitrate + intercept;
            ss_res += (dp.eight_over_a - predicted) * (dp.eight_over_a - predicted);
            ss_tot += (dp.eight_over_a - mean_y) * (dp.eight_over_a - mean_y);
        }
        double r_squared = 1.0 - (ss_res / ss_tot);

        std::cout << "  Linear fit: 8/a = " << slope << " * bitrate + " << intercept << "\n";
        std::cout << "  R² = " << r_squared << "\n";

        std::ofstream dataFile("plot_data_8a_scatter.tmp");
        for (size_t i = 0; i < aData.size(); i++) {
            dataFile << aData[i].sender_bitrate << " " << aData[i].eight_over_a << "\n";
        }
        dataFile.close();

        // Find min/max for ranges
        double min_8a = aData[0].eight_over_a, max_8a = aData[0].eight_over_a;
        double min_br = aData[0].sender_bitrate, max_br = aData[0].sender_bitrate;
        for (const auto& dp : aData) {
            if (dp.eight_over_a < min_8a) min_8a = dp.eight_over_a;
            if (dp.eight_over_a > max_8a) max_8a = dp.eight_over_a;
            if (dp.sender_bitrate < min_br) min_br = dp.sender_bitrate;
            if (dp.sender_bitrate > max_br) max_br = dp.sender_bitrate;
        }
        double y_margin = (max_8a - min_8a) * 0.1;
        double x_margin = (max_br - min_br) * 0.1;

        // Write regression line data points
        std::ofstream regFile("plot_data_8a_reg.tmp");
        regFile << min_br << " " << (slope * min_br + intercept) << "\n";
        regFile << max_br << " " << (slope * max_br + intercept) << "\n";
        regFile.close();

        std::ofstream gnuplotScript("plot_script_8a_scatter.gp");
        gnuplotScript << "set terminal png size 1000,600 enhanced font 'Arial,11'\n";
        gnuplotScript << "set output '8avsiPerf_regression.png'\n";
        gnuplotScript << "set title '8/a (data rate in Mbits/sec) vs iPerf3 Data Rate (R² = " << std::fixed << std::setprecision(4) << r_squared << ")'\n";
        gnuplotScript << "set xlabel 'iPerf3 Data Rate (Mbits/sec)'\n";
        gnuplotScript << "set ylabel '8/a (Mbits/sec)'\n";
        gnuplotScript << "set format y '%.4e'\n";
        gnuplotScript << "set grid\n";
        gnuplotScript << "set yrange [" << (min_8a - y_margin) << ":" << (max_8a + y_margin) << "]\n";
        gnuplotScript << "set xrange [" << (min_br - x_margin) << ":" << (max_br + x_margin) << "]\n";
        gnuplotScript << "plot 'plot_data_8a_scatter.tmp' using 1:2 with points pt 7 ps 1.5 lc rgb 'blue' title 'Trials', \\\n";
        gnuplotScript << "     'plot_data_8a_reg.tmp' using 1:2 with lines lc rgb 'red' lw 2 title 'Linear Fit'\n";
        gnuplotScript.close();

        int result = system("gnuplot plot_script_8a_scatter.gp");
        if (result == 0) {
            std::cout << "  Saved: 8avsiPerf_regression.png\n";
            fs::remove("plot_data_8a_scatter.tmp");
            fs::remove("plot_data_8a_reg.tmp");
            fs::remove("plot_script_8a_scatter.gp");
        } else {
            std::cerr << "  Error: gnuplot failed for 8/a regression plot\n";
        }
    }

    // ========== Graph 6: Dual-Axis Time Series (8/a and iPerf3 vs Time) ==========
    std::cout << "\nGraph 6: 8/a and iPerf3 Data Rate vs Time (Dual Axis)\n";
    std::cout << "  Valid data points: " << aData.size() << "\n";

    if (!aData.empty()) {
        std::ofstream dataFile("plot_data_8a_dual.tmp");
        for (size_t i = 0; i < aData.size(); i++) {
            dataFile << i << " " << aData[i].eight_over_a << " " << aData[i].sender_bitrate << "\n";
        }
        dataFile.close();

        std::ofstream gnuplotScript("plot_script_8a_dual.gp");
        gnuplotScript << "set terminal png size 1000,600 enhanced font 'Arial,11'\n";
        gnuplotScript << "set output '8avsiPerf.png'\n";
        gnuplotScript << "set title '8/a (Estimated) and iPerf3 Data Rate vs Run Time'\n";
        gnuplotScript << "set xlabel 'Run Time (Military Time)'\n";
        gnuplotScript << "set ylabel '8/a (Mbits/sec)' textcolor rgb 'blue'\n";
        gnuplotScript << "set y2label 'iPerf3 Data Rate (Mbits/sec)' textcolor rgb 'red'\n";
        gnuplotScript << "set ytics nomirror textcolor rgb 'blue'\n";
        gnuplotScript << "set y2tics nomirror textcolor rgb 'red'\n";
        gnuplotScript << "set format y '%.4e'\n";
        gnuplotScript << "set format y2 '%.1f'\n";
        gnuplotScript << "set grid\n";
        gnuplotScript << "set pointsize 1.5\n";
        gnuplotScript << "set xtics rotate by -45\n";

        gnuplotScript << "set xtics (";
        for (size_t i = 0; i < aData.size(); i++) {
            if (i > 0) gnuplotScript << ", ";
            gnuplotScript << "\"" << aData[i].time_label << "\" " << i;
        }
        gnuplotScript << ")\n";

        gnuplotScript << "set xrange [-0.5:" << (aData.size() - 0.5) << "]\n";
        gnuplotScript << "plot 'plot_data_8a_dual.tmp' using 1:2 with linespoints pt 7 lc rgb 'blue' title '8/a (left axis)', \\\n";
        gnuplotScript << "     'plot_data_8a_dual.tmp' using 1:3 axes x1y2 with linespoints pt 5 lc rgb 'red' title 'iPerf3 (right axis)'\n";
        gnuplotScript.close();

        int result = system("gnuplot plot_script_8a_dual.gp");
        if (result == 0) {
            std::cout << "  Saved: 8avsiPerf.png\n";
            fs::remove("plot_data_8a_dual.tmp");
            fs::remove("plot_script_8a_dual.gp");
        } else {
            std::cerr << "  Error: gnuplot failed for 8/a dual-axis plot\n";
        }
    }

    // ========== Graph 7: Linear vs Quadratic R² vs Run Number ==========
    std::cout << "\nGraph 7: Linear vs Quadratic R² vs Run Number\n";
    std::cout << "  Valid data points: " << allData.size() << "\n";

    if (!allData.empty()) {
        std::ofstream dataFile("plot_data_rsq.tmp");
        for (size_t i = 0; i < allData.size(); i++) {
            dataFile << i << " " << allData[i].linear_r_squared << " " << allData[i].quadratic_r_squared << "\n";
        }
        dataFile.close();

        std::ofstream gnuplotScript("plot_script_rsq.gp");
        gnuplotScript << "set terminal png size 1000,600 enhanced font 'Arial,11'\n";
        gnuplotScript << "set output 'RSquared_vs_Runtime.png'\n";
        gnuplotScript << "set title 'Linear vs Quadratic R² vs Run Number'\n";
        gnuplotScript << "set xlabel 'Run Time (Military Time)'\n";
        gnuplotScript << "set ylabel 'R²'\n";
        gnuplotScript << "set format y '%.6f'\n";
        gnuplotScript << "set grid\n";
        gnuplotScript << "set pointsize 1.5\n";
        gnuplotScript << "set xtics rotate by -45\n";
        gnuplotScript << "set key top left\n";

        gnuplotScript << "set xtics (";
        for (size_t i = 0; i < allData.size(); i++) {
            if (i > 0) gnuplotScript << ", ";
            gnuplotScript << "\"" << allData[i].time_label << "\" " << i;
        }
        gnuplotScript << ")\n";

        gnuplotScript << "set xrange [-0.5:" << (allData.size() - 0.5) << "]\n";
        gnuplotScript << "plot 'plot_data_rsq.tmp' using 1:2 with points pt 7 lc rgb 'blue' title 'Linear R²', \\\n";
        gnuplotScript << "     'plot_data_rsq.tmp' using 1:3 with points pt 5 lc rgb 'red' title 'Quadratic R²'\n";
        gnuplotScript.close();

        int result = system("gnuplot plot_script_rsq.gp");
        if (result == 0) {
            std::cout << "  Saved: RSquared_vs_Runtime.png\n";
            fs::remove("plot_data_rsq.tmp");
            fs::remove("plot_script_rsq.gp");
        } else {
            std::cerr << "  Error: gnuplot failed for R² plot\n";
        }
    }

    std::cout << "\nDone.\n";
    return 0;
}
