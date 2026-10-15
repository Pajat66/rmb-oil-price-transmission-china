"""Render saved figure inputs only. No model fitting or resampling is performed.

Figure 2 accepts a separately held, frozen monthly plotting source; it is never
copied into the repository. SI compatibility is retained but is outside the
main-figure visual redesign.
"""
from pathlib import Path
import argparse,csv,hashlib,importlib,json,sys,re
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/science'));sys.path.insert(0,str(ROOT/'src/plotting'))
from interface import external_directory,configure

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--figure',choices=['1','2','3','4','5','6','7','S1','S2','S3'],required=True)
    p.add_argument('--source-dir',type=Path,default=ROOT/'figures/source')
    p.add_argument('--statistics-dir',type=Path,default=ROOT/'reference/statistics')
    p.add_argument('--bootstrap-dir',type=Path,default=ROOT/'reference/bootstrap')
    p.add_argument('--work-dir',type=Path)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--private-held-figure2',action='store_true')
    p.add_argument('--figure2-source',type=Path,help='Private saved Figure 2 source CSV; no source construction')
    p.add_argument('--dpi',type=int,choices=range(300,601),default=600,help='TIFF resolution (default 600)')
    a=p.parse_args();out=external_directory(a.output_dir,'figure output',create=True)
    if list(out.iterdir()):p.error('Figure output directory must be empty')
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    font_manager.findfont('Arial',fallback_to_default=False)
    inputs=[]
    def read(path):
        inputs.append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        return pd.read_csv(path,float_precision='round_trip')
    def rows(path):
        inputs.append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
    status='PLOTTED_FROM_SAVED_STATISTICS_NOT_FULL_REPRODUCTION'
    if a.figure.startswith('S'):
        import si_plots as m
        class Sources(m.FrozenSources):
            def read(self,name):
                if name not in self.cache:
                    path=a.statistics_dir/name
                    if not path.is_file() and a.statistics_dir==ROOT/'reference/statistics':
                        mapping=json.loads((ROOT/'metadata/table_input_mapping.json').read_text(encoding='utf-8'));path=ROOT/mapping[name]['path']
                    self.cache[name]=(rows(path),hashlib.sha256(path.read_bytes()).hexdigest())
                return self.cache[name]
        plt.rcParams.update({'font.family':'Arial','font.size':8.5,'axes.labelsize':8.5,'xtick.labelsize':8,'ytick.labelsize':8,'axes.linewidth':.65})
        frozen=Sources(a.statistics_dir);manifest=[]
        if a.figure in ('S1','S2'):m.stability_grid(out,frozen,a.figure,a.figure=='S2',manifest)
        else:m.rolling_hierarchy(out,frozen,'S3',6,'SI',manifest)
        qa={'manifest':manifest}
    else:
        n=int(a.figure)
        if n==2 and not a.figure2_source:
            if not a.private_held_figure2 or not a.work_dir:p.error('Figure2 needs --work-dir and --private-held-figure2; publication remains HOLD_LICENSE_REVIEW')
            configure(a.work_dir)
        m=importlib.import_module(f'figure{n}_plot')
        if n==1:
            fig,ax,font=m.make_figure();qa=m.check_geometry(fig,ax)
        elif n==2:
            if a.figure2_source:
                source=read(a.figure2_source)
                assert len(source)==7774, 'Frozen Figure 2 source row count changed'
                audit={'source_mode':'saved private plotting source; no construction or model execution'}
            else:
                source,audit,provenance=m.build_sources()
                inputs.extend({'file':k,'sha256':v} for k,v in provenance.items())
            fig,statistics,qa=m.draw(source)
            qa.update({'audit':audit,'statistics':statistics})
            status='REDRAW_FROM_PRIVATE_FROZEN_SOURCE_AUTHOR_GRAPHIC_ONLY'
        elif n in (3,4,5):
            names={3:'figure_3_primary_lp_period_source.csv',4:'figure_4_cumulative_contrasts_source.csv',5:'figure_5_brent_fx_components_source.csv'}
            fig,qa=m.draw(rows(a.source_dir/names[n]))
        elif n==6:
            from scipy.stats import gaussian_kde
            source=read(a.source_dir/'figure_6_import_cost_innovative_source.csv')
            link=read(a.statistics_dir/'mechanism_link1_final.csv');selected=link[(link.quantity_order==-1)&(link.maxlags==12)]
            lags=selected[selected.record_type=='oil_lag'].sort_values('lag');total=selected[selected.record_type=='cumulative'].iloc[0]
            bootstrap_path=a.bootstrap_dir/'phase2b_bootstrap_paths_short_L12.npz'
            inputs.append({'file':bootstrap_path.name,'sha256':hashlib.sha256(bootstrap_path.read_bytes()).hexdigest()})
            arrays=np.load(bootstrap_path,allow_pickle=False);draws={};kdes={}
            for label,y in [('Fuel','d_fuel_power_inflation'),('PPI','d_ppi_inflation')]:
                path=arrays[f'MECH2_{y}_quantity0'];assert path.shape==(5000,13)
                for h,values in enumerate(np.cumsum(path,axis=1).T):
                    row=source[(source.outcome==label)&(source.lag_or_horizon.astype(str)==str(h))].iloc[0]
                    assert np.allclose(np.quantile(values,[.025,.975]),[row.ci_low,row.ci_high],rtol=0,atol=1e-14)
                    draws[label,h]=values;kdes[label,h]=gaussian_kde(values,bw_method='scott')
            fig,qa=m.plot(source,draws,kdes,lags,total)
        else:
            source=read(a.source_dir/'figure_7_temporal_stability_source.csv');summary=read(a.source_dir/'figure_7_temporal_stability_recursive_summary.csv')
            formal=source[source.diagnostic_type.isin(['SUP_WALD','RECURSIVE_CUSUM','HANSEN'])].copy();formal['test']=formal.diagnostic_type
            assert len(formal)==27 and sorted(formal.horizon.unique())==[0,3,6]
            fig,qa=m.plot(source,summary,formal)
        from visual_system import text_geometry,evidence_digest
        qa['final_geometry']=text_geometry(fig)
        if n in (3,4,6,7):qa['evidence_digest']=evidence_digest(fig)
        fig.savefig(out/f'Figure {n}.png',dpi=300)
        fig.savefig(out/f'Figure {n}.svg',metadata={'Date':None})
        # Expand Matplotlib CSS shorthand for portable font inspection/editing.
        svg_path=out/f'Figure {n}.svg'
        svg=svg_path.read_text(encoding='utf-8')
        svg=re.sub(r"font:\s*(?:(\d+)\s+)?([\d.]+)px\s+'Arial'",
            lambda m:f"font-family: Arial; font-size: {m.group(2)}px; font-weight: {m.group(1) or '400'}",svg)
        svg_path.write_text(svg,encoding='utf-8')
        fig.savefig(out/f'Figure {n}.eps')
        # Flatten to single-frame RGB, without alpha; preserve intended physical size.
        import io
        from PIL import Image
        buffer=io.BytesIO();fig.savefig(buffer,format='png',dpi=a.dpi);buffer.seek(0)
        image=Image.open(buffer).convert('RGB')
        image.save(out/f'Figure {n}.tif',compression='tiff_lzw',dpi=(a.dpi,a.dpi))
        qa['exports']={'TIFF_dpi':a.dpi,'PNG_dpi':300,'TIFF_mode':'RGB','TIFF_compression':'LZW',
            'dimensions_mm':list(fig.get_size_inches()*25.4),'formats':['TIFF','PNG','SVG','EPS']}
        plt.close(fig)
    (out/'render_receipt.json').write_text(json.dumps({'status':status,'figure':a.figure,'inputs':inputs,'checks':qa,'new_estimation':False},indent=2,default=lambda x:x.item() if hasattr(x,'item') else str(x)),encoding='utf-8')
    print(status)
if __name__=='__main__':main()
