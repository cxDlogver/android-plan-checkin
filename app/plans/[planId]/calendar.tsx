import { useLocalSearchParams } from 'expo-router';
import Calendar from '../../../src/features/calendar';
export default function Screen(){const {planId}=useLocalSearchParams<{planId:string}>();return <Calendar planId={planId}/>;}
