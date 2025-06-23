"""
FuseVault Benchmark Results Analyzer
Analyzes and compares benchmark results across multiple runs

Usage:
    python fusevault_results_analyzer.py [results_directory]
    python fusevault_results_analyzer.py --compare run1 run2 run3
    python fusevault_results_analyzer.py --trend results_dir1 results_dir2 results_dir3
"""

import argparse
import json
import os
import glob
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np


class FuseVaultResultsAnalyzer:
    """Analyzer for FuseVault benchmark results"""
    
    def __init__(self):
        self.results_data: List[Dict[str, Any]] = []
        self.comparison_targets = {
            "BigchainDB": {"tps": 298, "latency": 2855},
            "MongoDB YCSB Read": {"tps": 1200, "latency": 10},
            "MongoDB YCSB Write": {"tps": 100, "latency": 100},
            "IPFS Local": {"tps": 47, "latency": 21}
        }
    
    def load_results(self, results_paths: List[str]) -> None:
        """Load benchmark results from one or more directories"""
        
        for path in results_paths:
            path_obj = Path(path)
            
            if path_obj.is_file() and path_obj.name.endswith('_raw_results.json'):
                # Direct JSON file
                self._load_single_file(path_obj)
            elif path_obj.is_dir():
                # Directory - look for results files
                json_files = list(path_obj.glob("*_raw_results.json"))
                for json_file in json_files:
                    self._load_single_file(json_file)
            else:
                print(f"Warning: Could not find results in {path}")
    
    def _load_single_file(self, file_path: Path) -> None:
        """Load a single results JSON file"""
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Add metadata about the run
            run_info = {
                "file_path": str(file_path),
                "run_name": file_path.parent.name,
                "timestamp": self._extract_timestamp(file_path),
                "results": data
            }
            
            self.results_data.append(run_info)
            print(f"Loaded {len(data)} results from {file_path.name}")
            
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    
    def _extract_timestamp(self, file_path: Path) -> Optional[datetime]:
        """Try to extract timestamp from file path or name"""
        
        # Try to get modification time
        try:
            stat = file_path.stat()
            return datetime.fromtimestamp(stat.st_mtime)
        except:
            return None
    
    def generate_summary_report(self) -> str:
        """Generate a comprehensive summary report"""
        
        if not self.results_data:
            return "No results data loaded"
        
        report_lines = [
            "# FuseVault Benchmark Analysis Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total benchmark runs analyzed: {len(self.results_data)}",
            ""
        ]
        
        # Overall statistics
        all_results = []
        for run in self.results_data:
            all_results.extend(run["results"])
        
        if all_results:
            df = pd.DataFrame(all_results)
            
            report_lines.extend([
                "## Overall Performance Summary",
                f"- Total test cases: {len(all_results)}",
                f"- Average TPS: {df['transactions_per_second'].mean():.2f}",
                f"- Average Latency: {df['average_latency_ms'].mean():.2f}ms",
                f"- Average Success Rate: {df['success_rate'].mean():.1%}",
                f"- Best TPS: {df['transactions_per_second'].max():.2f}",
                f"- Best Latency: {df['average_latency_ms'].min():.2f}ms",
                ""
            ])
            
            # Performance by test type
            report_lines.extend(["## Performance by Test Type", ""])
            
            for test_type in df['test_type'].unique():
                test_data = df[df['test_type'] == test_type]
                report_lines.extend([
                    f"### {test_type.replace('_', ' ').title()}",
                    f"- Average TPS: {test_data['transactions_per_second'].mean():.2f}",
                    f"- Average Latency: {test_data['average_latency_ms'].mean():.2f}ms",
                    f"- Success Rate: {test_data['success_rate'].mean():.1%}",
                    f"- Test cases: {len(test_data)}",
                    ""
                ])
            
            # Industry comparison
            report_lines.extend(["## Industry Comparison", ""])
            
            fusevault_avg_tps = df['transactions_per_second'].mean()
            fusevault_avg_latency = df['average_latency_ms'].mean()
            
            for system, metrics in self.comparison_targets.items():
                tps_comparison = (fusevault_avg_tps / metrics["tps"]) * 100
                latency_comparison = (fusevault_avg_latency / metrics["latency"]) * 100
                
                report_lines.extend([
                    f"### vs {system}",
                    f"- TPS Performance: {tps_comparison:.1f}% of {system}",
                    f"- Latency Performance: {latency_comparison:.1f}% of {system}",
                    ""
                ])
            
            # Recommendations
            report_lines.extend(["## Recommendations", ""])
            
            if fusevault_avg_tps < 20:
                report_lines.append("- 🔴 **Low Throughput**: TPS below 20, investigate bottlenecks")
            elif fusevault_avg_tps < 50:
                report_lines.append("- 🟡 **Moderate Throughput**: TPS 20-50, room for improvement")
            else:
                report_lines.append("- 🟢 **Good Throughput**: TPS above 50, solid performance")
            
            if fusevault_avg_latency > 10000:
                report_lines.append("- 🔴 **High Latency**: >10s average, check network and config")
            elif fusevault_avg_latency > 5000:
                report_lines.append("- 🟡 **Elevated Latency**: 5-10s average, monitor for issues")
            else:
                report_lines.append("- 🟢 **Acceptable Latency**: <5s average, within expected range")
            
            avg_success = df['success_rate'].mean()
            if avg_success < 0.9:
                report_lines.append("- 🔴 **Low Success Rate**: <90%, investigate errors")
            elif avg_success < 0.95:
                report_lines.append("- 🟡 **Moderate Success Rate**: 90-95%, some reliability issues")
            else:
                report_lines.append("- 🟢 **High Success Rate**: >95%, excellent reliability")
        
        return '\n'.join(report_lines)
    
    def create_performance_charts(self, output_dir: Path) -> None:
        """Create comprehensive performance visualization charts"""
        
        if not self.results_data:
            print("No data to chart")
            return
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Combine all results into one dataframe
        all_results = []
        for run in self.results_data:
            for result in run["results"]:
                result_copy = result.copy()
                result_copy['run_name'] = run['run_name']
                result_copy['timestamp'] = run['timestamp']
                all_results.append(result_copy)
        
        if not all_results:
            print("No results to chart")
            return
        
        df = pd.DataFrame(all_results)
        
        # Set up the plotting style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # Create comprehensive analysis charts
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        
        # 1. TPS by Test Type
        ax1 = axes[0, 0]
        test_type_tps = df.groupby('test_type')['transactions_per_second'].mean().sort_values(ascending=False)
        bars = ax1.bar(range(len(test_type_tps)), test_type_tps.values, color='skyblue', edgecolor='navy')
        ax1.set_title('Average TPS by Test Type')
        ax1.set_ylabel('Transactions Per Second')
        ax1.set_xticks(range(len(test_type_tps)))
        ax1.set_xticklabels([t.replace('_', '\n') for t in test_type_tps.index], rotation=0, ha='center')
        
        # Add value labels
        for bar, value in zip(bars, test_type_tps.values):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                    f'{value:.1f}', ha='center', va='bottom')
        
        # 2. Latency Distribution
        ax2 = axes[0, 1]
        latency_cols = ['average_latency_ms', 'p95_latency_ms', 'p99_latency_ms']
        latency_data = [df[col].mean() for col in latency_cols if col in df.columns]
        latency_labels = ['Average', 'P95', 'P99']
        
        bars = ax2.bar(latency_labels[:len(latency_data)], latency_data, 
                      color=['lightblue', 'orange', 'red'], alpha=0.7)
        ax2.set_title('Latency Distribution')
        ax2.set_ylabel('Latency (ms)')
        
        # Add value labels
        for bar, value in zip(bars, latency_data):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                    f'{value:.0f}', ha='center', va='bottom')
        
        # 3. Success Rate by Concurrent Clients
        ax3 = axes[0, 2]
        if 'concurrent_clients' in df.columns:
            client_performance = df.groupby('concurrent_clients').agg({
                'success_rate': 'mean',
                'transactions_per_second': 'mean'
            })
            
            ax3.plot(client_performance.index, client_performance['success_rate'] * 100, 
                    'o-', linewidth=2, markersize=8, color='green')
            ax3.set_xlabel('Concurrent Clients')
            ax3.set_ylabel('Success Rate (%)')
            ax3.set_title('Success Rate vs Concurrency')
            ax3.grid(True, alpha=0.3)
            ax3.set_ylim(0, 105)
        
        # 4. Performance vs Data Size
        ax4 = axes[1, 0]
        if 'data_size_bytes' in df.columns:
            size_impact = df.groupby('data_size_bytes')['average_latency_ms'].mean()
            ax4.plot(size_impact.index, size_impact.values, 'o-', linewidth=2, markersize=8, color='purple')
            ax4.set_xlabel('Data Size (bytes)')
            ax4.set_ylabel('Average Latency (ms)')
            ax4.set_title('Latency vs Data Size')
            ax4.set_xscale('log')
            ax4.grid(True, alpha=0.3)
        
        # 5. Industry Comparison
        ax5 = axes[1, 1]
        fusevault_tps = df['transactions_per_second'].mean()
        
        systems = ['FuseVault'] + list(self.comparison_targets.keys())
        tps_values = [fusevault_tps] + [target["tps"] for target in self.comparison_targets.values()]
        
        colors = ['green'] + ['orange'] * len(self.comparison_targets)
        bars = ax5.bar(systems, tps_values, color=colors, alpha=0.7)
        ax5.set_title('TPS Comparison vs Industry')
        ax5.set_ylabel('TPS')
        ax5.tick_params(axis='x', rotation=45)
        
        # Add value labels
        for bar, value in zip(bars, tps_values):
            height = bar.get_height()
            ax5.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                    f'{value:.0f}', ha='center', va='bottom')
        
        # 6. Performance Over Time (if multiple runs)
        ax6 = axes[1, 2]
        if len(self.results_data) > 1:
            run_performance = []
            for run in self.results_data:
                if run["results"]:
                    run_df = pd.DataFrame(run["results"])
                    avg_tps = run_df['transactions_per_second'].mean()
                    run_performance.append({
                        'run_name': run['run_name'],
                        'timestamp': run['timestamp'],
                        'avg_tps': avg_tps
                    })
            
            if run_performance:
                perf_df = pd.DataFrame(run_performance)
                ax6.plot(range(len(perf_df)), perf_df['avg_tps'], 'o-', linewidth=2, markersize=8)
                ax6.set_xlabel('Benchmark Run')
                ax6.set_ylabel('Average TPS')
                ax6.set_title('Performance Trend Over Time')
                ax6.set_xticks(range(len(perf_df)))
                ax6.set_xticklabels([name[:10] for name in perf_df['run_name']], rotation=45)
                ax6.grid(True, alpha=0.3)
        else:
            ax6.text(0.5, 0.5, 'Single Run\n(No Trend Data)', 
                    ha='center', va='center', transform=ax6.transAxes, fontsize=12)
            ax6.set_title('Performance Trend')
        
        plt.tight_layout()
        plt.savefig(output_dir / "fusevault_analysis_comprehensive.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # Create detailed comparison chart
        self._create_detailed_comparison_chart(df, output_dir)
        
        print(f"Charts saved to {output_dir}")
    
    def _create_detailed_comparison_chart(self, df: pd.DataFrame, output_dir: Path):
        """Create detailed comparison chart"""
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Performance matrix heatmap
        ax1 = axes[0, 0]
        if len(df) > 0:
            # Create performance matrix
            perf_matrix = df.groupby(['test_type', 'concurrent_clients']).agg({
                'transactions_per_second': 'mean'
            }).unstack(fill_value=0)
            
            if not perf_matrix.empty:
                sns.heatmap(perf_matrix, annot=True, fmt='.1f', cmap='YlOrRd', ax=ax1)
                ax1.set_title('TPS Heatmap: Test Type vs Concurrency')
                ax1.set_xlabel('Concurrent Clients')
                ax1.set_ylabel('Test Type')
        
        # Latency vs TPS scatter
        ax2 = axes[0, 1]
        scatter = ax2.scatter(df['transactions_per_second'], df['average_latency_ms'], 
                             c=df['success_rate'], cmap='RdYlGn', alpha=0.7, s=100)
        ax2.set_xlabel('TPS')
        ax2.set_ylabel('Average Latency (ms)')
        ax2.set_title('Performance Trade-off: TPS vs Latency')
        plt.colorbar(scatter, ax=ax2, label='Success Rate')
        
        # System efficiency (TPS/Latency ratio)
        ax3 = axes[1, 0]
        df['efficiency'] = df['transactions_per_second'] / df['average_latency_ms'] * 1000
        test_efficiency = df.groupby('test_type')['efficiency'].mean().sort_values(ascending=False)
        
        bars = ax3.bar(range(len(test_efficiency)), test_efficiency.values, color='lightgreen', alpha=0.7)
        ax3.set_title('System Efficiency (TPS per Second of Latency)')
        ax3.set_ylabel('Efficiency Score')
        ax3.set_xticks(range(len(test_efficiency)))
        ax3.set_xticklabels([t.replace('_', '\n') for t in test_efficiency.index], rotation=0)
        
        # Performance distribution
        ax4 = axes[1, 1]
        ax4.hist(df['transactions_per_second'], bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        ax4.axvline(df['transactions_per_second'].mean(), color='red', linestyle='--', 
                   label=f'Mean: {df["transactions_per_second"].mean():.1f}')
        ax4.set_xlabel('TPS')
        ax4.set_ylabel('Frequency')
        ax4.set_title('TPS Distribution')
        ax4.legend()
        
        plt.tight_layout()
        plt.savefig(output_dir / "fusevault_analysis_detailed.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def compare_runs(self, run_names: List[str]) -> str:
        """Compare specific benchmark runs"""
        
        if len(run_names) < 2:
            return "Need at least 2 runs to compare"
        
        comparison_data = []
        for run in self.results_data:
            if run['run_name'] in run_names:
                if run['results']:
                    run_df = pd.DataFrame(run['results'])
                    comparison_data.append({
                        'run_name': run['run_name'],
                        'avg_tps': run_df['transactions_per_second'].mean(),
                        'avg_latency': run_df['average_latency_ms'].mean(),
                        'avg_success_rate': run_df['success_rate'].mean(),
                        'total_tests': len(run_df)
                    })
        
        if not comparison_data:
            return "No matching runs found"
        
        df = pd.DataFrame(comparison_data)
        
        report = ["# Run Comparison Report", ""]
        
        for _, row in df.iterrows():
            report.extend([
                f"## {row['run_name']}",
                f"- Average TPS: {row['avg_tps']:.2f}",
                f"- Average Latency: {row['avg_latency']:.2f}ms",
                f"- Success Rate: {row['avg_success_rate']:.1%}",
                f"- Total Tests: {row['total_tests']}",
                ""
            ])
        
        # Best performing run
        best_tps_run = df.loc[df['avg_tps'].idxmax()]
        best_latency_run = df.loc[df['avg_latency'].idxmin()]
        
        report.extend([
            "## Summary",
            f"- Best TPS: {best_tps_run['run_name']} ({best_tps_run['avg_tps']:.2f})",
            f"- Best Latency: {best_latency_run['run_name']} ({best_latency_run['avg_latency']:.2f}ms)",
            ""
        ])
        
        return '\n'.join(report)


def main():
    """Main execution function"""
    
    parser = argparse.ArgumentParser(description='FuseVault Benchmark Results Analyzer')
    parser.add_argument('paths', nargs='*', 
                       help='Paths to results directories or JSON files')
    parser.add_argument('--compare', nargs='+',
                       help='Compare specific runs by name')
    parser.add_argument('--output', default='analysis_output',
                       help='Output directory for generated reports and charts')
    
    args = parser.parse_args()
    
    if not args.paths:
        # Default: look for results in current directory
        args.paths = glob.glob("**/fusevault_benchmark_results*", recursive=True)
        if not args.paths:
            print("No results found. Please specify results directories.")
            return
    
    analyzer = FuseVaultResultsAnalyzer()
    analyzer.load_results(args.paths)
    
    if not analyzer.results_data:
        print("No valid results data found")
        return
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate summary report
    summary = analyzer.generate_summary_report()
    
    with open(output_dir / "fusevault_analysis_summary.md", 'w') as f:
        f.write(summary)
    
    print("📊 Analysis Summary:")
    print(summary)
    
    # Generate charts
    analyzer.create_performance_charts(output_dir)
    
    # Run comparison if requested
    if args.compare:
        comparison = analyzer.compare_runs(args.compare)
        
        with open(output_dir / "fusevault_run_comparison.md", 'w') as f:
            f.write(comparison)
        
        print("\n📈 Run Comparison:")
        print(comparison)
    
    print(f"\n✅ Analysis complete! Reports saved to {output_dir}")


if __name__ == "__main__":
    main()