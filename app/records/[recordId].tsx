import { useLocalSearchParams } from 'expo-router';
import RecordForm from '../../src/features/record-form';
export default function Screen(){const {planId,recordId}=useLocalSearchParams<{planId:string;recordId:string}>();return <RecordForm planId={planId} recordId={recordId}/>;}
