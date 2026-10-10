import { useLocalSearchParams } from 'expo-router';
import RecordForm from '../../src/features/record-form';
export default function Screen(){const {planId,businessOn,result}=useLocalSearchParams<{planId:string;businessOn?:string;result?:string}>();return <RecordForm planId={planId} businessOn={businessOn} preset={result}/>;}
