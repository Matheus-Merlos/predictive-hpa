# Scripts para limpar os dados que o predictive-hpa gerou, para poder gerar os gráficos certinho
import re
import pandas as pd

def clear_duplicates(input_file: str, output_file: str) -> None:
    seen_lines = set()
    
    log_pattern = re.compile(r'^\[INFO\] - \d{4}-\d{2}-\d{2}')

    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8') as outfile:
        
        for line in infile:
            clean_line = line.strip()
            
            if not clean_line:
                continue
                
            if log_pattern.match(clean_line):
                if clean_line not in seen_lines:
                    outfile.write(line)
                    seen_lines.add(clean_line)
            else:
                outfile.write(line)

    print(f'Cleanup completed! {len(seen_lines)} unique logs saved to {output_file}.')

def parse_logs_to_dataframe(input_file: str, output_file: str) -> None:
    data = []
    current_entry = {}

    def extract_val(pattern, line, type_func=float):
        match = re.search(pattern, line)
        return type_func(match.group(1)) if match else None

    with open(input_file, 'r') as f:
        for line in f:
            ts_match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line)
            if not ts_match: continue
            ts = ts_match.group(0)

            if current_entry and current_entry.get('timestamp') != ts:
                if 'final_replicas' in current_entry: data.append(current_entry)
                current_entry = {'timestamp': ts}
            else:
                if 'timestamp' not in current_entry: current_entry = {'timestamp': ts}

            if 'Metrics:' in line:
                current_entry['cpu'] = extract_val(r'CPU=([\d\.]+)', line)
                current_entry['mem'] = extract_val(r'Mem: ([\d\.]+)GB', line)
            
            if 'Predicted CPU' in line:
                current_entry['pred_cpu'] = extract_val(r'Predicted CPU \(\+15m\): ([\d\.]+)', line)
                current_entry['pred_mem'] = extract_val(r'Predicted MEM \(\+15m\): ([\d\.]+)', line)
                current_entry['pred_replicas'] = extract_val(r'Needed: (\d+)', line, int)
                current_entry['reactive_replicas'] = extract_val(r'Reactive calculated: (\d+)', line, int)

            if 'Shadow Mode Suggestion' in line:
                current_entry['final_replicas'] = extract_val(r'replicas to (\d+)', line, int)
                current_entry['engine'] = re.search(r'Engine: (.*?)\)', line).group(1) if 'Engine: ' in line else 'UNKNOWN'

    df = pd.DataFrame(data)
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['model_version'] = 'Base_HPA_Burro'
    df.loc[df['timestamp'] >= '2026-06-25 13:09:00', 'model_version'] = 'Preditivo_CPU_15m'
    df.loc[df['timestamp'] >= '2026-06-26 13:53:00', 'model_version'] = 'Preditivo_CPU_MEM_15m'
    
    df.to_csv(output_file, index=False)

if __name__ == '__main__':
    # clear_duplicates('data.log', 'sanitized-data.log')
    parse_logs_to_dataframe('sanitized-data.log', 'analytics_data.csv')