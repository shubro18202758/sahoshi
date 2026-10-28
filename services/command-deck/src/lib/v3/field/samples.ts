/**
 * The sample stills a camera page can read (static/samples/cameras, credits in its NOTICE.md). No live CCTV frame
 * reaches Sahoshi, so every one is shown labelled "Sample still · not live" with its credit beside it. Faces and legible
 * plates are pixelated in the files themselves. tests/field.unit.mjs holds this list, the files and the notice equal.
 */
export interface SampleStill {
	id: string;
	src: string;
	/** What it shows, in English (the alt text and the board entry's note). */
	caption: string;
	author: string;
	licence: string;
	licenceUrl: string;
	source: string;
}

const COMMONS = 'https://commons.wikimedia.org/wiki/File:';

export const SAMPLE_STILLS: readonly SampleStill[] = [
	{
		id: 'waterlogged_kolkata',
		src: '/samples/cameras/waterlogged_kolkata.jpg',
		caption: 'Kolkata, September 2021: a street under rainwater',
		author: 'Sumita Roy Dutta',
		licence: 'CC BY-SA 4.0',
		licenceUrl: 'https://creativecommons.org/licenses/by-sa/4.0',
		source: `${COMMONS}Torrential_rain_lash_Kolkata,_many_areas_waterlogged-_Kolkata-West_Bengal-September_2021-IMG_20210915_205028.jpg`,
	},
	{
		id: 'amphan_shyambazar_09',
		src: '/samples/cameras/amphan_shyambazar_09.jpg',
		caption: 'Shyambazar after Cyclone Amphan: branches and wires on the road',
		author: 'Indrajit Das',
		licence: 'CC BY-SA 4.0',
		licenceUrl: 'https://creativecommons.org/licenses/by-sa/4.0',
		source: `${COMMONS}Post_Cyclone_Amphan_situation_of_Shyambazar_in_Kolkata_09.jpg`,
	},
	{
		id: 'jam_park_circus',
		src: '/samples/cameras/jam_park_circus.jpg',
		caption: 'Park Circus seven-point crossing, evening traffic',
		author: 'Biswarup Ganguly',
		licence: 'CC BY 3.0',
		licenceUrl: 'https://creativecommons.org/licenses/by/3.0',
		source: `${COMMONS}Traffic_Jam_-_Park_Circus_Seven-point_Crossing_-_Kolkata_20170825180423.jpg`,
	},
	{
		id: 'tree_howrah',
		src: '/samples/cameras/tree_howrah.jpg',
		caption: "Howrah after a nor'wester: an uprooted tree across the road",
		author: 'Biswarup Ganguly',
		licence: 'CC BY-SA 4.0',
		licenceUrl: 'https://creativecommons.org/licenses/by-sa/4.0',
		source: `${COMMONS}Fallen_Bodhi_Tree_-_2018-04-17_Norwester_Aftermath_-_Padmapukur_Water_Treatment_Plant_Road_-_Howrah_20180418081122.jpg`,
	},
	{
		id: 'jam_esplanade',
		src: '/samples/cameras/jam_esplanade.jpg',
		caption: 'SN Banerjee Road at Esplanade',
		author: 'Biswarup Ganguly',
		licence: 'CC BY 3.0',
		licenceUrl: 'https://creativecommons.org/licenses/by/3.0',
		source: `${COMMONS}Traffic_Jam_-_Esplanade_-_SN_Banerjee_Road_-_Kolkata_2016-06-23_5136.JPG`,
	},
	{
		id: 'clear_belgharia',
		src: '/samples/cameras/clear_belgharia.jpg',
		caption: 'Belgharia Expressway, an empty carriageway',
		author: 'seaview99',
		licence: 'CC BY-SA 2.0',
		licenceUrl: 'https://creativecommons.org/licenses/by-sa/2.0',
		source: `${COMMONS}Belgharia_Expressway,Kolkata_1.jpg`,
	},
];

/** A sample per camera, stable for the camera (so a page always opens on the same still). */
export function sampleFor(cameraId: string | null | undefined): SampleStill {
	let h = 0;
	for (const ch of String(cameraId ?? '')) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
	return SAMPLE_STILLS[h % SAMPLE_STILLS.length];
}

/** What an officer might say, per spoken language (the sheet's "Try saying"; data, not UI copy). */
export const SPOKEN_EXAMPLES: Readonly<Record<'bn' | 'en' | 'hi', string>> = {
	bn: 'গড়িয়াহাট মোড়ে হাঁটু জল, বাস আটকে আছে।',
	en: 'Knee-deep water at Gariahat crossing, a bus is stuck.',
	hi: 'गड़ियाहाट मोड़ पर घुटनों तक पानी, बस फँसी है।',
};
