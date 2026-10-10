import { useLocalSearchParams } from 'expo-router';
import PlanForm from '../../../src/features/plan-form';
export default function Screen(){const {planId}=useLocalSearchParams<{planId:string}>();return <PlanForm planId={planId}/>;}
