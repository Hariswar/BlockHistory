// Key for the map's symbols. Search-only entries appear once there is a search.
export default function MapLegend({ searched }: { searched: boolean }) {
  return (
    <div className="legend" aria-label="Map key">
      {searched && (
        <>
          <span>
            <i className="dot high" /> Often linked to contamination
          </span>
          <span>
            <i className="dot medium" /> Sometimes linked
          </span>
          <span>
            <i className="dot home" /> Address you searched
          </span>
          <span>
            <i className="ring" /> 100 m search area
          </span>
        </>
      )}
      <span>
        <i className="outline" /> Area covered so far
      </span>
    </div>
  );
}
