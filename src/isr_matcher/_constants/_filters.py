"""This script defines strings used for sending requests to respective source of infrastructure data while applying certain filter criteria"""

### ISR - Infrastrukturregister der Deutschen Bahn

ISR_EQUALS_TRACK = """
<wfs:GetFeature
	xmlns:wfs="http://www.opengis.net/wfs" service="WFS" version="1.1.0" viewParams="LANG:DE;JAHR:2024;ALG_DBNETZ_STRECKE:DB Strecken" outputFormat="json"
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd">
	<wfs:Query typeName="feature:ISR_V_GEO_TEN_KLASSIFIZIERUNG" srsName="EPSG:31467"
		xmlns:feature="http://bahn.de/ISR">
		<ogc:Filter
			xmlns:ogc="http://www.opengis.net/ogc">
			<ogc:And>
				<ogc:PropertyIsEqualTo matchCase="false">
					<ogc:PropertyName>ISR_STRE_NR</ogc:PropertyName>
					<ogc:Literal>$arg1</ogc:Literal>
				</ogc:PropertyIsEqualTo>
			</ogc:And>
		</ogc:Filter>
	</wfs:Query>
</wfs:GetFeature>
"""

ISR_EQUALS_TRACK_SEGMENT = """
<wfs:GetFeature
	xmlns:wfs="http://www.opengis.net/wfs" service="WFS" version="1.1.0" viewParams="LANG:DE;JAHR:2024" outputFormat="json"
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd">
	<wfs:Query typeName="feature:ISR_V_GEO_TEN_KLASSIFIZIERUNG" srsName="EPSG:31467"
		xmlns:feature="http://bahn.de/ISR">
		<ogc:Filter
			xmlns:ogc="http://www.opengis.net/ogc">
			<ogc:And>
				<ogc:PropertyIsEqualTo matchCase="false">
					<ogc:PropertyName>ISR_STRE_NR</ogc:PropertyName>
					<ogc:Literal>$arg1</ogc:Literal>
				</ogc:PropertyIsEqualTo>
                <ogc:PropertyIsLike  wildCard="*" singleChar="." escape="!">
					<ogc:PropertyName>ISR_STRECKE_VON_BIS</ogc:PropertyName>
					<ogc:Literal>$arg2</ogc:Literal>
				</ogc:PropertyIsLike>
			</ogc:And>
		</ogc:Filter>
	</wfs:Query>
</wfs:GetFeature>
"""


ISR_EQUALS_OP = """
<wfs:GetFeature 
	xmlns:wfs="http://www.opengis.net/wfs" service="WFS" version="1.1.0" outputFormat="json" maxFeatures="300" viewParams="LANG:DE;JAHR:2024;ALG_DBNETZ_STRECKE:DB Strecken" 
    xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
		<wfs:Query typeName="feature:ISR_V_GEO_BETRIEBSSTELLEN_PUNKT" srsName="EPSG:31467"
			xmlns:feature="http://bahn.de/ISR">
			<ogc:Filter
				xmlns:ogc="http://www.opengis.net/ogc">
				<ogc:And>
					<ogc:PropertyIsLike  wildCard="*" singleChar="." escape="!">
						<ogc:PropertyName>BST_STELLE_NAME</ogc:PropertyName>
						<ogc:Literal>$arg1</ogc:Literal>
					</ogc:PropertyIsLike>
					<ogc:PropertyIsEqualTo matchCase="false">
						<ogc:PropertyName>STRNR</ogc:PropertyName>
						<ogc:Literal>$arg2</ogc:Literal>
					</ogc:PropertyIsEqualTo>
				</ogc:And>
			</ogc:Filter>
		</wfs:Query>
    
</wfs:GetFeature>
"""

ISR_EQUALS_TRANSITION = """
<wfs:GetFeature 
	xmlns:wfs="http://www.opengis.net/wfs" service="WFS" version="1.1.0" outputFormat="json" maxFeatures="5000" viewParams="LANG:DE;JAHR:2024;ALG_DBNETZ_STRECKE:DB Strecken" 
    xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <wfs:Query typeName="feature:ISR_V_GEO_STRECKENUEBERGAENGE" srsName="EPSG:31467"
		xmlns:feature="http://bahn.de/ISR">
		<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
			<ogc:Or>
				<ogc:And>
					<ogc:PropertyIsLike  wildCard="*" singleChar="." escape="!">
						<ogc:PropertyName>BST_STELLE_NAME</ogc:PropertyName>
						<ogc:Literal>$arg1</ogc:Literal>
					</ogc:PropertyIsLike>
					<ogc:PropertyIsEqualTo matchCase="false">
						<ogc:PropertyName>STRECKE1</ogc:PropertyName>
						<ogc:Literal>$arg2</ogc:Literal>
					</ogc:PropertyIsEqualTo>
				</ogc:And>
				<ogc:And>
					<ogc:PropertyIsLike  wildCard="*" singleChar="." escape="!">
						<ogc:PropertyName>BST_STELLE_NAME</ogc:PropertyName>
						<ogc:Literal>$arg1</ogc:Literal>
					</ogc:PropertyIsLike>
					<ogc:PropertyIsEqualTo matchCase="false">
						<ogc:PropertyName>STRECKE2</ogc:PropertyName>
						<ogc:Literal>$arg2</ogc:Literal>
					</ogc:PropertyIsEqualTo>
				</ogc:And>
			</ogc:Or>
		</ogc:Filter>
	</wfs:Query>
</wfs:GetFeature>
"""


# x1, y1, x2, y2
# lat_min, lon_min, lat_max, lon_max filter=%3Cogc%3AFilter%20xmlns%3Aogc%3D%22http%3A%2F%2Fwww.opengis.net%2Fogc%22%3E%3Cogc%3AIntersects%3E%3Cogc%3APropertyName%3E__GEOMETRY_COLUMN_NAME_PLACEHOLDER__%3C%2Fogc%3APropertyName%3E%3Cgml%3APolygon%20xmlns%3Agml%3D%22http%3A%2F%2Fwww.opengis.net%2Fgml%22%20srsName%3D%22EPSG%3A31467%22%3E%3Cgml%3Aexterior%3E%3Cgml%3ALinearRing%3E%3Cgml%3AposList%3E3524777.7168237%206068285.6557352%203524777.7168237%206068303.9957352%203524719.8968237005%206068303.9957352%203524719.8968237005%206068285.6557352%203524777.7168237%206068285.6557352%3C%2Fgml%3AposList%3E%3C%2Fgml%3ALinearRing%3E%3C%2Fgml%3Aexterior%3E%3C%2Fgml%3APolygon%3E%3C%2Fogc%3AIntersects%3E%3C%2Fogc%3AFilter%3E&featuretypes=ISR%3AISR_V_GEO_BETRIEBSSTELLEN_PUNKT&featuretypes=ISR%3AISR_V_GEO_STRECKENUEBERGAENGE&featuretypes=ISR%3AISR_V_GEO_TEN_KLASSIFIZIERUNG&featuretypes=HINTERGRUNDKARTEN%3Aosm_gk3&geomnameplacehoder=__GEOMETRY_COLUMN_NAME_PLACEHOLDER__&slds=DEFAULT&slds=DEFAULT&slds=DEFAULT&slds=DEFAULT&targetSrs=EPSG%3A31467&scale=500&drillDown=true&featureIDS=&qualifiedSelectionLayerName=&viewparams=undefined%3Aundefined%3BLANG%3ADE%3BALG_DBNETZ_STRECKE%3ADB%20Strecken%3BJAHR%3A2024&viewparams=undefined%3Aundefined%3BLANG%3ADE%3BALG_DBNETZ_STRECKE%3ADB%20Strecken%3BJAHR%3A2024&viewparams=undefined%3Aundefined%3BLANG%3ADE%3BALG_DBNETZ_STRECKE%3ADB%20Strecken%3BJAHR%3A2024&viewparams=undefined%3BLANG%3ADE&parentName=V_GEO_BETRIEBSSTELLEN&parentName=&parentName=V_GEO_STRECKENABSCHNITTE&parentName=&childName=&childName=&childName=&childName=&application=ISR&application=&application=ISR&application=&id=&id=&id=&id=&LANG=DE
ISR_TRACKS_IN_BBOX = """
<wfs:GetFeature
	xmlns:wfs="http://www.opengis.net/wfs" service="WFS" version="1.1.0" viewParams="LANG:DE;JAHR:2024;ALG_DBNETZ_STRECKE:DB Strecken" outputFormat="json"
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd">
	<wfs:Query typeName="feature:ISR_V_GEO_TEN_KLASSIFIZIERUNG" srsName="EPSG:31467"
		xmlns:feature="http://bahn.de/ISR">
		<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
				<ogc:Intersects>
					<ogc:PropertyName>GEOMETRIE</ogc:PropertyName>
					<gml:Polygon xmlns:gml="http://www.opengis.net/gml" srsName="EPSG:31467">
						<gml:exterior>
							<gml:LinearRing>
								<gml:posList>$arg1 $arg2 $arg3 $arg2 $arg3 $arg4 $arg1 $arg4 $arg1 $arg2</gml:posList>
							</gml:LinearRing>
						</gml:exterior>
					</gml:Polygon>
				</ogc:Intersects>
		</ogc:Filter>
	</wfs:Query>
</wfs:GetFeature>
"""

ISR_OP_IN_BBOX = """
<wfs:GetFeature
	xmlns:wfs="http://www.opengis.net/wfs" service="WFS" version="1.1.0" viewParams="LANG:DE;JAHR:2024;ALG_DBNETZ_STRECKE:DB Strecken" outputFormat="json"
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd">
	<wfs:Query typeName="feature:ISR_V_GEO_BETRIEBSSTELLEN_PUNKT" srsName="EPSG:31467"
		xmlns:feature="http://bahn.de/ISR">
		<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
				<ogc:Intersects>
					<ogc:PropertyName>GEOMETRIE_PUNKT</ogc:PropertyName>
					<gml:Polygon xmlns:gml="http://www.opengis.net/gml" srsName="EPSG:31467">
						<gml:exterior>
							<gml:LinearRing>
								<gml:posList>$arg1 $arg2 $arg3 $arg2 $arg3 $arg4 $arg1 $arg4 $arg1 $arg2</gml:posList>
							</gml:LinearRing>
						</gml:exterior>
					</gml:Polygon>
				</ogc:Intersects>
		</ogc:Filter>
	</wfs:Query>
</wfs:GetFeature>
"""

ISR_TRANSITIONS_IN_BBOX = """
<wfs:GetFeature
	xmlns:wfs="http://www.opengis.net/wfs" service="WFS" version="1.1.0" viewParams="LANG:DE;JAHR:2024;ALG_DBNETZ_STRECKE:DB Strecken" outputFormat="json"
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd">
	<wfs:Query typeName="feature:ISR_V_GEO_STRECKENUEBERGAENGE" srsName="EPSG:31467"
		xmlns:feature="http://bahn.de/ISR">
		<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
				<ogc:Intersects>
					<ogc:PropertyName>GEOMETRIE_PUNKT</ogc:PropertyName>
					<gml:Polygon xmlns:gml="http://www.opengis.net/gml" srsName="EPSG:31467">
						<gml:exterior>
							<gml:LinearRing>
								<gml:posList>$arg1 $arg2 $arg3 $arg2 $arg3 $arg4 $arg1 $arg4 $arg1 $arg2</gml:posList>
							</gml:LinearRing>
						</gml:exterior>
					</gml:Polygon>
				</ogc:Intersects>
		</ogc:Filter>
	</wfs:Query>
</wfs:GetFeature>
"""

ISR_TUNNEL_IN_BBOX = """
<wfs:GetFeature
	xmlns:wfs="http://www.opengis.net/wfs" service="WFS" version="1.1.0" viewParams="LANG:DE;JAHR:2024;ALG_DBNETZ_STRECKE:DB Strecken" outputFormat="json"
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd">
	<wfs:Query typeName="feature:ISR_V_GEO_TUNNEL" srsName="EPSG:31467"
		xmlns:feature="http://bahn.de/ISR">
		<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
				<ogc:Intersects>
					<ogc:PropertyName>GEOMETRIE</ogc:PropertyName>
					<gml:Polygon xmlns:gml="http://www.opengis.net/gml" srsName="EPSG:31467">
						<gml:exterior>
							<gml:LinearRing>
								<gml:posList>$arg1 $arg2 $arg3 $arg2 $arg3 $arg4 $arg1 $arg4 $arg1 $arg2</gml:posList>
							</gml:LinearRing>
						</gml:exterior>
					</gml:Polygon>
				</ogc:Intersects>
		</ogc:Filter>
	</wfs:Query>
</wfs:GetFeature>
"""

ISR_TRACKS_IN_BOUNDARY = """
<wfs:GetFeature
	xmlns:wfs="http://www.opengis.net/wfs" service="WFS" version="1.1.0" viewParams="LANG:DE;JAHR:2024;ALG_DBNETZ_STRECKE:DB Strecken" outputFormat="json"
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd">
	<wfs:Query typeName="feature:ISR_V_GEO_TEN_KLASSIFIZIERUNG" srsName="EPSG:31467"
		xmlns:feature="http://bahn.de/ISR">
		<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
				<ogc:Intersects>
					<ogc:PropertyName>GEOMETRIE</ogc:PropertyName>
					<gml:Polygon xmlns:gml="http://www.opengis.net/gml" srsName="EPSG:31467">
						<gml:exterior>
							<gml:LinearRing>
								<gml:posList>$arg1</gml:posList>
							</gml:LinearRing>
						</gml:exterior>
					</gml:Polygon>
				</ogc:Intersects>
		</ogc:Filter>
	</wfs:Query>
</wfs:GetFeature>
"""

ISR_OP_IN_BOUNDARY = """
<wfs:GetFeature
	xmlns:wfs="http://www.opengis.net/wfs" service="WFS" version="1.1.0" viewParams="LANG:DE;JAHR:2024;ALG_DBNETZ_STRECKE:DB Strecken" outputFormat="json"
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd">
	<wfs:Query typeName="feature:ISR_V_GEO_BETRIEBSSTELLEN_PUNKT" srsName="EPSG:31467"
		xmlns:feature="http://bahn.de/ISR">
		<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
				<ogc:Intersects>
					<ogc:PropertyName>GEOMETRIE_PUNKT</ogc:PropertyName>
					<gml:Polygon xmlns:gml="http://www.opengis.net/gml" srsName="EPSG:31467">
						<gml:exterior>
							<gml:LinearRing>
								<gml:posList>$arg1</gml:posList>
							</gml:LinearRing>
						</gml:exterior>
					</gml:Polygon>
				</ogc:Intersects>
		</ogc:Filter>
	</wfs:Query>
</wfs:GetFeature>
"""

ISR_TRANSITIONS_IN_BOUNDARY = """
<wfs:GetFeature
	xmlns:wfs="http://www.opengis.net/wfs" service="WFS" version="1.1.0" viewParams="LANG:DE;JAHR:2024;ALG_DBNETZ_STRECKE:DB Strecken" outputFormat="json"
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd">
	<wfs:Query typeName="feature:ISR_V_GEO_STRECKENUEBERGAENGE" srsName="EPSG:31467"
		xmlns:feature="http://bahn.de/ISR">
		<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
				<ogc:Intersects>
					<ogc:PropertyName>GEOMETRIE_PUNKT</ogc:PropertyName>
					<gml:Polygon xmlns:gml="http://www.opengis.net/gml" srsName="EPSG:31467">
						<gml:exterior>
							<gml:LinearRing>
								<gml:posList>$arg1</gml:posList>
							</gml:LinearRing>
						</gml:exterior>
					</gml:Polygon>
				</ogc:Intersects>
		</ogc:Filter>
	</wfs:Query>
</wfs:GetFeature>
"""

ISR_TUNNEL_IN_BOUNDARY = """
<wfs:GetFeature
	xmlns:wfs="http://www.opengis.net/wfs" service="WFS" version="1.1.0" viewParams="LANG:DE;JAHR:2024;ALG_DBNETZ_STRECKE:DB Strecken" outputFormat="json"
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd">
	<wfs:Query typeName="feature:ISR_V_GEO_TUNNEL" srsName="EPSG:31467"
		xmlns:feature="http://bahn.de/ISR">
		<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
				<ogc:Intersects>
					<ogc:PropertyName>GEOMETRIE</ogc:PropertyName>
					<gml:Polygon xmlns:gml="http://www.opengis.net/gml" srsName="EPSG:31467">
						<gml:exterior>
							<gml:LinearRing>
								<gml:posList>$arg1</gml:posList>
							</gml:LinearRing>
						</gml:exterior>
					</gml:Polygon>
				</ogc:Intersects>
		</ogc:Filter>
	</wfs:Query>
</wfs:GetFeature>
"""


ISR_BOUNDARY = """
<wfs:GetFeature
	xmlns:wfs="http://www.opengis.net/wfs" 
	service="WFS" 
	version="1.1.0" 
	outputFormat="json"
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
	xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd">
	
	<wfs:Query typeName="feature:ISR_V_GEO_TEN_KLASSIFIZIERUNG" srsName="EPSG:31467"
		xmlns:feature="http://bahn.de/ISR">
		<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
				<ogc:Intersects>
					<ogc:PropertyName>GEOMETRIE</ogc:PropertyName>
					<gml:Polygon xmlns:gml="http://www.opengis.net/gml" srsName="EPSG:31467">
						<gml:exterior>
							<gml:LinearRing>
								<gml:posList>$arg1</gml:posList>
							</gml:LinearRing>
						</gml:exterior>
					</gml:Polygon>
				</ogc:Intersects>
		</ogc:Filter>
	</wfs:Query>
	
	<wfs:Query typeName="feature:ISR_V_GEO_BETRIEBSSTELLEN_PUNKT" srsName="EPSG:31467"
		xmlns:feature="http://bahn.de/ISR">
		<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
				<ogc:Intersects>
					<ogc:PropertyName>GEOMETRIE_PUNKT</ogc:PropertyName>
					<gml:Polygon xmlns:gml="http://www.opengis.net/gml" srsName="EPSG:31467">
						<gml:exterior>
							<gml:LinearRing>
								<gml:posList>$arg1</gml:posList>
							</gml:LinearRing>
						</gml:exterior>
					</gml:Polygon>
				</ogc:Intersects>
		</ogc:Filter>
	</wfs:Query>
	
	<wfs:Query typeName="feature:ISR_V_GEO_STRECKENUEBERGAENGE" srsName="EPSG:31467"
		xmlns:feature="http://bahn.de/ISR">
		<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
			<ogc:Intersects>
				<ogc:PropertyName>GEOMETRIE_PUNKT</ogc:PropertyName>
				<gml:Polygon xmlns:gml="http://www.opengis.net/gml" srsName="EPSG:31467">
					<gml:exterior>
						<gml:LinearRing>
							<gml:posList>$arg1</gml:posList>
						</gml:LinearRing>
					</gml:exterior>
				</gml:Polygon>
			</ogc:Intersects>
		</ogc:Filter>
	</wfs:Query>

	<wfs:Query typeName="feature:ISR_V_GEO_TUNNEL" srsName="EPSG:31467"
		xmlns:feature="http://bahn.de/ISR">
		<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
			<ogc:Intersects>
				<ogc:PropertyName>GEOMETRIE</ogc:PropertyName>
				<gml:Polygon xmlns:gml="http://www.opengis.net/gml" srsName="EPSG:31467">
					<gml:exterior>
						<gml:LinearRing>
							<gml:posList>$arg1</gml:posList>
						</gml:LinearRing>
					</gml:exterior>
				</gml:Polygon>
			</ogc:Intersects>
		</ogc:Filter>
	</wfs:Query>
	
</wfs:GetFeature>
"""

ISR_FILTERS = {
    "EQUALS_TRACK": ISR_EQUALS_TRACK,
    "EQUALS_TRACK_SEG": ISR_EQUALS_TRACK_SEGMENT,
    "EQUALS_OP": ISR_EQUALS_OP,
    "EQUALS_TRANSITION": ISR_EQUALS_TRANSITION,
    "TRACKS_IN_BBOX": ISR_TRACKS_IN_BBOX,
    "OP_IN_BBOX": ISR_OP_IN_BBOX,
    "TRANSITIONS_IN_BBOX": ISR_TRANSITIONS_IN_BBOX,
    "TUNNEL_IN_BBOX": ISR_TUNNEL_IN_BBOX,
    "TRACKS_IN_BOUNDARY": ISR_TRACKS_IN_BOUNDARY,
    "OP_IN_BOUNDARY": ISR_OP_IN_BOUNDARY,
    "TRANSITIONS_IN_BOUNDARY": ISR_TRANSITIONS_IN_BOUNDARY,
    "TUNNEL_IN_BOUNDARY": ISR_TUNNEL_IN_BOUNDARY,
}

ISR_EXCEPTIONAL_STATION_NAMES = [
    "Berlin Hauptbahnhof - Lehrter Bahnhof",
    "Berlin Hauptbahnhof - Lehrter Bf  S-Bahn",
    "Mainz - Römisches Theater",
    "Mering - Sankt Afra",
    "Priemerburg - NUP Güstrow",
    "St Margarethen                   (Holst)",
    "Hamburg-Ottensen                (S-Bahn)",
    "Hamburg-Stellingen              (S-Bahn)",
    "Hamburg-Eidelstedt              (S-Bahn)",
    "Pinneberg                       (S-Bahn)",
    "Hamburg-Langenfelde             (S-Bahn)",
    "Hamburg Dammtor                 (S-Bahn)",
    "Hamburg Sternschanze            (S-Bahn)",
    "Hamburg Berliner Tor          (Landwehr)",
    "Hamburg Hbf                     (S-Bahn)",
    "Hamburg Hasselbrook             (S-Bahn)",
    "Hamburg-Ohlsdorf                (S-Bahn)",
    "Hamburg-Barmbek                 (S-Bahn)",
    "Hamburg-Rothenburgsort          (S-Bahn)",
    "Hamburg-Allermöhe               (S-Bahn)",
    "Hamburg Berliner Tor         (Bergedorf)",
    "Hamburg-Bergedorf               (S-Bahn)",
    "Hamburg-Altona                  (S-Bahn)",
    "Hamburg-Veddel                  (S-Bahn)",
    "Hamburg-Harburg                 (S-Bahn)",
    "Hamburg-Wilhelmsburg            (S-Bahn)",
    "Hamburg-Neugraben               (S-Bahn)",
    "Hamburg-Hausbruch               (S-Bahn)",
    "Letter                            (Abzw)",
    "Meckelfeld                            Hp",
    "Kassel-Oberzwehren                (Abzw)",
    "Empelde                           (Abzw)",
    "Himmelsthür                       (Abzw)",
    "Weddel                            (Abzw)",
    "Dortmund-Körne                    (Abzw)",
    "Dortmund-Dorstfeld              (S-Bahn)",
    "Bochum-Langendreer              (S-Bahn)",
    "Dortmund-Lütgendortmund         (S-Bahn)",
    "Essen-Dellwig                     (Abzw)",
    "Köln Steinstraße                  (Abzw)",
    "Meerbeck                          (Abzw)",
    "Duisburg-Hochfeld Süd               (Hp)",
    "Krefeld-Uerdingen                   (Hp)",
    "Wuppertal-Langerfeld                (Hp)",
    "Haan-Gruiten                      (Abzw)",
    "Düsseldorf-Bilk                     (Hp)",
    "Hochdahl                          (Abzw)",
    "Dormagen Chempark         (Südbahnsteig)",
    "Dormagen Chempark        (Nordbahnsteig)",
    "Köln-Nippes                       (Abzw)",
    "Köln-Lövenich                     S-Bahn",
    "Selmig                            (Abzw)",
    "Köln Messe/Deutz (tief)",
    "Köln Messe/Deutz Bft            (S-Bahn)",
    "Düsseldorf Flughafen                (Hp)",
    "Hörne DB-Grenze                  (Plang)",
    "Löhne (Westf) Pbf",
    "Völklingen Walzwerke              (Abzw)",
    "Eisenberg (Pfalz) Bahnsteig  West",
    "Forsthaus                    (Frankfurt)",
    "Gießen Licher Straße",
    "Frankfurt-Zehn Ruten",
    "Ubstadt-Weiher                    (Abzw)",
    "Bürstadt                            (Hp)",
    "Warthausen                          (Hp)",
    "Sigmaringendorf                     (Hp)",
    "Reutlingen - RTunlimited",
    "Wernfeld                            (Hp)",
    "Regensburg-Prüfening               (NRH)",
    "Maxhütte-Haidhof             (DB-Grenze)",
    "Nürnberg-Dutzendteich                 Hp",
    "Nürnberg-Reichelsdorf           (S-Bahn)",
    "Nürnberg-Reichelsdorf              (Üst)",
    "Nürnberg-Eibach                 (S-Bahn)",
    "Büchenbach                         (Üst)",
    "Nürnberg-Eibach                    (Üst)",
    "Schwabach-Limbach                  (Üst)",
    "Rednitzhembach                     (Üst)",
    "Berlin-Karow                      S-Bahn",
    "Berlin-Pankow                     S-Bahn",
    "Bernau (b Berlin)                 S-Bahn",
    "Berlin-Blankenburg                S-Bahn",
    "Berlin-Gesundbrunnen              S-Bahn",
    "Berlin-Karlshorst                 S-Bahn",
    "Erkner                            S-Bahn",
    "Berlin-Köpenick                   S-Bahn",
    "Berlin Ostbahnhof                 S-Bahn",
    "Berlin-Karow West                 S-Bahn",
    "Fredersdorf (b Berlin)            S-Bahn",
    "Berlin-Lichtenberg                S-Bahn",
    "Hoppegarten (Mark)                S-Bahn",
    "Berlin-Baumschulenweg             S-Bahn",
    "Zeuthen                           S-Bahn",
    "Berlin-Grünau                     S-Bahn",
    "Berlin-Schöneweide                S-Bahn",
    "Flughafen BER - Schoenefeld T5 (S-Bahn)",
    "Flughafen BER - Terminal 1-2   (S-Bahn)",
    "Schönfließ                        S-Bahn",
    "Berlin-Marzahn                    S-Bahn",
    "Ahrensfelde                       S-Bahn",
    "Berlin-Hohenschönhausen           S-Bahn",
    "Berlin-Neukölln                   S-Bahn",
    "Berlin Schönhauser Allee          S-Bahn",
    "Berlin-Halensee                   S-Bahn",
    "Berlin Jungfernheide            (S-Bahn)",
    "Berlin-Moabit",
    "Berlin Frankfurter Allee          S-Bahn",
    "Berlin Greifswalder Straße        S-Bahn",
    "Berlin-Tempelhof                  S-Bahn",
    "Berlin-Wedding                  (S-Bahn)",
    "Berlin-Charlottenburg             S-Bahn",
    "Berlin Friedrichstraße (Stadtb)   S-Bahn",
    "Berlin Alexanderplatz             S-Bahn",
    "Potsdam Hbf                       S-Bahn",
    "Berlin-Wannsee                    S-Bahn",
    "Potsdam Griebnitzsee              S-Bahn",
    "Berlin-Grunewald                  S-Bahn",
    "Berlin Zoologischer Garten        S-Bahn",
    "Berlin-Spandau                    S-Bahn",
    "Berlin-Schönholz                  S-Bahn",
    "Oranienburg                       S-Bahn",
    "Birkenwerder (b Berlin)           S-Bahn",
    "Berlin Julius-Leber-Brücke            SB",
    "Berlin Potsdamer Platz          (S-Bahn)",
    "Berlin Yorckstraße/Großgörschenstraße",
    "Berlin-Lichterfelde West          S-Bahn",
    "Berlin-Lichterfelde Ost         (S-Bahn)",
    "Blankenfelde (Kr Teltow-Fläming)  S-Bahn",
    "Halle-Silberhöhe                (S-Bahn)",
    "Werbig                 (Bahnsteig unten)",
    "Strausberg Stadt                   (STE)",
    "Berlin-Schönholz                     Bft",
    "Berlin Wollankstraße                Bft",
    "Finkenkrug                         (Afi)",
    "Hamburg-Billwerder-Moorfleet      (Abzw)",
    "Berlin Hauptbahnhof-Lehrter Bf  (Stadtb)",
    "Wilhelmshorst                     (Abzw)",
    "Flughafen BER - Schoenefeld T5   (Fern)",
    "Rückersdorf                    (Niederl)",
    "Weißkeißel",
    "Flughafen BER - Terminal 1-2      (Fern",
    "Berlin-Rahnsdorf                   (Üst)",
    "Wiesenau                          (Abzw)",
    "Wiesenau                              Hp",
    "Werbig                  (Bahnsteig oben)",
    "Hennigsdorf (b Berlin)            S-Bahn",
    "Coswig (Anh)                          Hp",
    "Cottbus-Merzdorf                Süd-Nord",
    "Dresden-Niedersedlitz Hp           (DHD)",
    "Dresden-Niedersedlitz Güteranlage  (DHD)",
    "Dresden-Pieschen                  (Abzw)",
    "Dresden-Cotta                     (Bstg)",
    "Radebeul-Naundorf                 (Abzw)",
    "Langendorf                     (Stralsd)",
    "Weißig (b Großenhain)",
    "Leipzig-Semmelweisstraße",
    "Grünbach                         (Vogtl)",
    "Groß Schwaß",
    "Stade DB-Grenze                  (Plang)",
]

# ISR_SYNOMYMS = {
#    "Wustermark Rbf Wot": "Wustermark Rbf",
# }


### OSM - OpenStreetMap

OSM_EQUALS_TRACK = f"""
	[out:json];
	(
		way[railway=rail][ref="$arg1"](47.40724, 5.98815, 54.9079, 14.98853);
		relation[ref="$arg1"](47.40724, 5.98815, 54.9079, 14.98853);
	);
	(._;>;);
	out;
"""

OSM_EQUALS_OP = f""""""

OSM_TRACKS_IN_BBOX = f"""

"""

OSM_OP_IN_BBOX = """

"""

OSM_TRANSITIONS_IN_BBOX = """

"""

OSM_BBOX = """
	[out:json];
	(
	way[railway=rail]($arg1, $arg2, $arg3, $arg4);
	node[railway=milestone]($arg1, $arg2, $arg3, $arg4);
	node[railway=switch]($arg1, $arg2, $arg3, $arg4);
	node[railway=stop]($arg1, $arg2, $arg3, $arg4);
	node[railway=halt]($arg1, $arg2, $arg3, $arg4);
	node[railway=station]($arg1, $arg2, $arg3, $arg4);
	);
	(._; >;);
	out;
"""

OSM_FILTERS = {
    "EQUALS_TRACK": OSM_EQUALS_TRACK,
    "EQUALS_OP": OSM_EQUALS_OP,
    "TRACKS_IN_BBOX": OSM_TRACKS_IN_BBOX,
    "SP_IN_BBOX": OSM_OP_IN_BBOX,
    "TRANSITIONS_IN_BBOX": OSM_TRANSITIONS_IN_BBOX,
    "BBOX": OSM_BBOX,
}
